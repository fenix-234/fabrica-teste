#!/usr/bin/env python3
"""
Analisa os dados do ensaio de alcance LoRa e recalibra o modelo.

Entradas (CSV):
  --gateway  o que o gateway recebeu:  ts_utc,seq,sf,rssi_dbm,snr_db,freq_mhz
  --no       o que o no registrou localmente: ts_utc,seq,sf,lat,lon,hdop,sats,bateria_v,posicao_corpo
             (o log local do no e obrigatorio: quando o enlace cai, a posicao
             nao chega ao gateway, e e justamente essa a posicao que interessa)

Saidas:
  - taxa de entrega (PDR) e RSSI mediano por faixa de distancia e por SF
  - expoente de perda de percurso ajustado por minimos quadrados
  - distancia de PDR 90% e 50% por SF  -> a resposta do ensaio
  - fator de calibracao recalculado para tools/cobertura/comparar_tecnologias.py
  - perda por posicao no corpo, se o log tiver mais de uma posicao

Sem dependencias externas.
"""

import argparse, csv, math, statistics, sys
from collections import defaultdict

R_TERRA = 6371000.0
K_REFRACAO = 4.0/3.0

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2-p1)/2)**2 +
         math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2)
    return 2*R_TERRA*math.asin(math.sqrt(a))/1000.0

def horizonte_km(ht, hr):
    return (math.sqrt(2*K_REFRACAO*R_TERRA*ht) + math.sqrt(2*K_REFRACAO*R_TERRA*hr))/1000.0

def num(v, padrao=None):
    try:
        return float(str(v).strip().replace(",", "."))
    except (ValueError, AttributeError, TypeError):
        return padrao

def ler(caminho):
    with open(caminho, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))

def ajuste_linear(xs, ys):
    """Minimos quadrados y = a + b*x. Devolve (a, b, r2)."""
    n = len(xs)
    if n < 3:
        return None, None, None
    mx, my = sum(xs)/n, sum(ys)/n
    sxx = sum((x-mx)**2 for x in xs)
    if sxx == 0:
        return None, None, None
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/sxx
    a = my - b*mx
    ss_tot = sum((y-my)**2 for y in ys)
    ss_res = sum((y-(a+b*x))**2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else None
    return a, b, r2

def cruzamento(bins, limiar):
    """Maior distancia em que o PDR ainda esta acima do limiar, exigindo que
    nao volte a subir depois (evita premiar um pico isolado no fim)."""
    ok = [d for d, pdr, _ in bins if pdr >= limiar]
    if not ok:
        return None
    return max(ok)

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gateway", required=True)
    p.add_argument("--no", required=True, dest="no")
    p.add_argument("--gw-lat", type=float, required=True)
    p.add_argument("--gw-lon", type=float, required=True)
    p.add_argument("--gw-altura", type=float, required=True, help="altura da antena do gateway, em m")
    p.add_argument("--h-no", type=float, default=0.8, help="altura da antena do no sobre a agua")
    p.add_argument("--bin-km", type=float, default=0.5)
    p.add_argument("--pdr-alvo", type=float, default=0.9, help="limiar de rastreio confiavel")
    p.add_argument("--saida", default="ensaio_resultado.csv")
    a = p.parse_args()

    gw = ler(a.gateway)
    no = ler(a.no)
    if not no:
        sys.exit("ERRO: log do no vazio.")

    recebidos = defaultdict(dict)      # sf -> seq -> (rssi, snr)
    for r in gw:
        sf = (r.get("sf") or "").strip().upper()
        seq = (r.get("seq") or "").strip()
        if not sf or not seq:
            continue
        recebidos[sf][seq] = (num(r.get("rssi_dbm")), num(r.get("snr_db")))

    # cada transmissao registrada pelo no vira uma amostra
    amostras = []              # (sf, dist_km, entregue, rssi, snr, posicao)
    sem_fix = 0
    for r in no:
        sf = (r.get("sf") or "").strip().upper()
        seq = (r.get("seq") or "").strip()
        lat, lon = num(r.get("lat")), num(r.get("lon"))
        if lat is None or lon is None or (lat == 0 and lon == 0):
            sem_fix += 1
            continue
        d = haversine_km(a.gw_lat, a.gw_lon, lat, lon)
        rssi = snr = None
        entregue = seq in recebidos.get(sf, {})
        if entregue:
            rssi, snr = recebidos[sf][seq]
        amostras.append((sf, d, entregue, rssi, snr,
                         (r.get("posicao_corpo") or "").strip().lower()))

    if not amostras:
        sys.exit("ERRO: nenhuma amostra com posicao valida.")

    sfs = sorted(set(s[0] for s in amostras), key=lambda x: int(x.replace("SF", "") or 0))
    dmax = max(s[1] for s in amostras)
    print("=" * 92)
    print("ENSAIO DE ALCANCE LoRa")
    print("=" * 92)
    print("gateway em %.5f, %.5f  |  antena a %.1f m  |  no a %.1f m" %
          (a.gw_lat, a.gw_lon, a.gw_altura, a.h_no))
    print("horizonte de radio teorico: %.1f km" % horizonte_km(a.gw_altura, a.h_no))
    print("amostras: %d  |  descartadas por falta de fix: %d  |  distancia maxima atingida: %.1f km"
          % (len(amostras), sem_fix, dmax))

    linhas_saida = []
    resumo = {}
    for sf in sfs:
        sub = [s for s in amostras if s[0] == sf]
        bins = []
        b = 0.0
        while b < dmax:
            faixa = [s for s in sub if b <= s[1] < b + a.bin_km]
            if faixa:
                ent = [s for s in faixa if s[2]]
                pdr = len(ent)/len(faixa)
                rssis = [s[3] for s in ent if s[3] is not None]
                med = statistics.median(rssis) if rssis else None
                bins.append((b + a.bin_km/2, pdr, med))
                linhas_saida.append({"sf": sf, "dist_km": round(b + a.bin_km/2, 3),
                                     "n": len(faixa), "pdr": round(pdr, 3),
                                     "rssi_mediano": round(med, 1) if med is not None else ""})
            b += a.bin_km
        if not bins:
            continue

        # O ajuste so pode usar a regiao NAO censurada. Onde o PDR ja caiu, o
        # gateway so registra os pacotes que pegaram desvanecimento favoravel,
        # e o RSSI mediano fica artificialmente alto -- isso achata a curva e
        # subestima o expoente. Ajustar apenas onde quase tudo chega.
        PDR_LIMPO = 0.9
        pts = [(d, m) for d, pdr, m in bins if m is not None and d > 0.2 and pdr >= PDR_LIMPO]
        n_exp = r2 = None
        n_bins_fit = len(pts)
        if n_bins_fit >= 3:
            xs = [10*math.log10(d) for d, _ in pts]
            ys = [m for _, m in pts]
            _, b_coef, r2 = ajuste_linear(xs, ys)
            if b_coef is not None:
                n_exp = -b_coef      # RSSI = A - 10n log10(d)

        d90 = cruzamento(bins, a.pdr_alvo)
        d50 = cruzamento(bins, 0.5)
        resumo[sf] = (d90, d50, n_exp, r2)

        print("\n--- %s ---" % sf)
        print("%9s %7s %7s %12s" % ("dist km", "n", "PDR", "RSSI mediano"))
        for d, pdr, med in bins:
            barra = "#" * int(round(pdr*20))
            print("%9.2f %7d %6.0f%% %12s  %s"
                  % (d, sum(1 for s in sub if d - a.bin_km/2 <= s[1] < d + a.bin_km/2),
                     pdr*100, ("%.0f dBm" % med) if med is not None else "-", barra))
        print("PDR >= %.0f%% ate: %s   |   PDR >= 50%% ate: %s"
              % (a.pdr_alvo*100,
                 ("%.2f km" % d90) if d90 else "nao atingido",
                 ("%.2f km" % d50) if d50 else "nao atingido"))
        if n_exp:
            print("expoente de perda de percurso: n = %.2f  (R2 = %.3f, %d faixas com PDR >= %.0f%%)"
                  % (n_exp, r2, n_bins_fit, PDR_LIMPO*100))
            if n_exp < 2.6:
                print("  -> proximo de espaco livre (n=2): duto de evaporacao ou antena muito alta")
            elif n_exp > 4.6:
                print("  -> pior que dois raios (n=4): obstrucao, mar formado ou antena mal instalada")
            elif n_exp >= 3.4:
                print("  -> compativel com o modelo de dois raios (n=4)")
            else:
                print("  -> entre espaco livre e dois raios: propagacao melhor que a prevista")
        elif n_bins_fit < 3:
            print("expoente nao ajustado: so %d faixa(s) com PDR >= %.0f%%."
                  % (n_bins_fit, PDR_LIMPO*100))
            print("  -> reduzir --bin-km ou refazer o transecto mais devagar")

    # ---------------- recalibracao do modelo
    print("\n" + "=" * 92)
    print("RECALIBRACAO DO MODELO")
    print("=" * 92)
    SENS = {"SF7": -125.0, "SF9": -131.0, "SF10": -133.0, "SF12": -139.0}
    TX_NO, G_NO, G_GW, MARGEM = 20.0, -2.0, 6.0, 10.0
    print("%-6s %14s %14s %12s %12s" %
          ("SF", "medido (PDR90)", "modelo atual", "fator atual", "fator novo"))
    print("-" * 62)
    fatores = []
    for sf in sfs:
        if sf not in SENS or sf not in resumo:
            continue
        d90 = resumo[sf][0]
        if not d90:
            continue
        perda_corpo = 10.0
        orc = (TX_NO + G_NO - perda_corpo) + G_GW - SENS[sf] - MARGEM
        dois_raios = (10 ** ((orc + 20*math.log10(a.gw_altura) + 20*math.log10(a.h_no))/40))/1000.0
        teto = horizonte_km(a.gw_altura, a.h_no)
        modelo = min(dois_raios*1.5, teto)
        novo = min(d90/dois_raios, 99) if dois_raios > 0 else None
        fatores.append(novo)
        print("%-6s %13.2f km %13.2f km %12.2f %12.2f" % (sf, d90, modelo, 1.5, novo))
    if fatores:
        f = statistics.median(fatores)
        print("\nfator de calibracao recomendado: %.2f  (atual: 1.50)" % f)
        print("aplicar com:  --fator-calibracao %.2f  em estimar_cobertura.py" % f)
        if abs(f - 1.5) > 0.5:
            print("ATENCAO: desvio grande do valor assumido. Refazer o estudo de cobertura")
            print("         das praias com o novo fator antes de qualquer decisao.")

    # ---------------- perda por posicao no corpo
    # So faz sentido comparar posicoes medidas na MESMA distancia e no MESMO SF.
    # Procura automaticamente a faixa em que o ensaio estatico foi feito: aquela
    # com o maior numero de posicoes distintas bem amostradas.
    JANELA_KM = 0.5
    MIN_AMOSTRAS = 5
    grupos = defaultdict(lambda: defaultdict(list))     # (sf, faixa) -> pos -> [rssi]
    for sf, d, ent, rssi, snr, pos in amostras:
        if ent and rssi is not None and pos:
            grupos[(sf, round(d/JANELA_KM))][pos].append(rssi)

    melhor_chave = None
    melhor_peso = 0
    for chave, porpos in grupos.items():
        validas = {p: v for p, v in porpos.items() if len(v) >= MIN_AMOSTRAS}
        if len(validas) < 2:
            continue
        peso = len(validas)*1000 + min(len(v) for v in validas.values())
        if peso > melhor_peso:
            melhor_peso, melhor_chave = peso, chave

    if melhor_chave:
        sf_c, faixa = melhor_chave
        validas = {p: v for p, v in grupos[melhor_chave].items() if len(v) >= MIN_AMOSTRAS}
        print("\n" + "=" * 92)
        print("PERDA POR POSICAO NO CORPO")
        print("=" * 92)
        print("comparacao em %s, a %.1f km do gateway (janela de %.1f km)"
              % (sf_c, faixa*JANELA_KM, JANELA_KM))
        base = max(statistics.median(v) for v in validas.values())
        print("%-26s %8s %14s %12s" % ("posicao", "n", "RSSI mediano", "perda"))
        for pos, vals in sorted(validas.items(), key=lambda kv: -statistics.median(kv[1])):
            med = statistics.median(vals)
            print("%-26s %8d %11.1f dBm %9.1f dB" % (pos, len(vals), med, base - med))
        print("\nO modelo assume 10 dB entre 'no ar' e 'bolsa estanque no corpo'.")
        print("E o parametro mais incerto de todas as contas: se o medido for muito")
        print("diferente, refazer o estudo de cobertura antes de qualquer decisao.")
    elif any(pos for _, _, ent, _, _, pos in amostras if ent):
        print("\nPerda por posicao nao calculada: nao ha duas posicoes com pelo menos")
        print("%d amostras na mesma faixa de %.1f km e no mesmo SF." % (MIN_AMOSTRAS, JANELA_KM))
        print("Fazer o ensaio estatico com o barco ancorado num ponto fixo.")

    with open(a.saida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["sf", "dist_km", "n", "pdr", "rssi_mediano"])
        w.writeheader()
        for r in linhas_saida:
            w.writerow(r)
    print("\ncurvas gravadas em %s" % a.saida)

if __name__ == "__main__":
    main()
