#!/usr/bin/env python3
"""
Analisa o ensaio de capacidade do gateway LoRa.

Entradas (CSV):
  --nos       tudo que os nos transmitiram: rodada,t_s,no_id,seq,sf,canal,classe,intervalo_s
  --gateway   o que o gateway recebeu:      rodada,t_s,no_id,seq,sf,canal,rssi_dbm,snr_db

A pergunta do ensaio nao e "qual a taxa de entrega media". E:

    a partir de quantos praticantes o gateway comeca a sacrificar
    justamente o mais distante?

Por causa do efeito de captura, o pacote mais forte sobrevive a colisao. Os nos
perto da praia sao os fortes; o praticante longe, derivando, e o fraco. Uma
taxa agregada de 95% pode esconder 40% no nó que mais precisa ser ouvido.

Por isso o relatorio traz, para cada rodada: taxa por classe de distancia, taxa
do pior no, e o indice de justica de Jain.

Sem dependencias externas.
"""
import argparse, csv, math, sys
from collections import defaultdict

def airtime_s(sf, pl_bytes=25, bw_khz=125, cr=1, preamble=8, crc=1, ih=0):
    tsym = (2**sf)/(bw_khz*1000.0)
    de = 1 if (sf >= 11 and bw_khz == 125) else 0
    n = 8 + max(math.ceil((8*pl_bytes - 4*sf + 28 + 16*crc - 20*ih)/(4.0*(sf-2*de)))*(cr+4), 0)
    return ((preamble + 4.25)*tsym) + n*tsym

def wilson(rec, tot, z=1.96):
    """Intervalo de confianca de Wilson para uma proporcao. Com poucas dezenas
    de pacotes, a taxa de entrega tem incerteza grande -- reportar o ponto sem
    o intervalo faz o ensaio decidir no ruido."""
    if tot == 0:
        return (0.0, 1.0)
    ph = rec/tot
    d = 1 + z*z/tot
    centro = (ph + z*z/(2*tot))/d
    meio = z*math.sqrt(ph*(1-ph)/tot + z*z/(4*tot*tot))/d
    return (max(0.0, centro-meio), min(1.0, centro+meio))

def n_para_precisao(p=0.9, meia_largura=0.05, z=1.96):
    return int(math.ceil(z*z*p*(1-p)/(meia_largura**2)))

def jain(valores):
    """1,0 = todos iguais; 1/n = um no leva tudo."""
    v = [x for x in valores if x is not None]
    if not v:
        return None
    soma = sum(v)
    soma_q = sum(x*x for x in v)
    return (soma*soma)/(len(v)*soma_q) if soma_q > 0 else None

def num(v, padrao=None):
    try:
        return float(str(v).strip().replace(",", "."))
    except (ValueError, AttributeError, TypeError):
        return padrao

def ler(caminho):
    with open(caminho, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))

ORDEM_CLASSE = {"perto": 0, "medio": 1, "longe": 2, "limite": 3}

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nos", required=True)
    p.add_argument("--gateway", required=True)
    p.add_argument("--canais", type=int, default=8)
    p.add_argument("--pdr-alvo", type=float, default=0.9,
                   help="taxa de entrega minima exigida do PIOR no")
    p.add_argument("--min-pacotes", type=int, default=20,
                   help="pacotes minimos para um no entrar na estatistica")
    p.add_argument("--saida", default="capacidade_resultado.csv")
    a = p.parse_args()

    tx = ler(a.nos)
    rx = ler(a.gateway)
    if not tx:
        sys.exit("ERRO: log dos nos vazio.")

    recebidos = set()
    for r in rx:
        recebidos.add((r.get("rodada"), r.get("no_id"), r.get("seq")))

    rodadas = defaultdict(lambda: {"por_no": defaultdict(lambda: [0, 0]),
                                   "classe_do_no": {}, "sf_do_no": {},
                                   "intervalo": None, "intervalos": set(), "airtime": 0.0,
                                   "t_min": None, "t_max": None})
    for r in tx:
        rod = r.get("rodada")
        no = r.get("no_id")
        d = rodadas[rod]
        d["por_no"][no][1] += 1
        if (rod, no, r.get("seq")) in recebidos:
            d["por_no"][no][0] += 1
        d["classe_do_no"][no] = (r.get("classe") or "").strip() or "?"
        sf = (r.get("sf") or "SF10").upper().replace("SF", "")
        try:
            sfi = int(sf)
        except ValueError:
            sfi = 10
        d["sf_do_no"][no] = sfi
        d["airtime"] += airtime_s(sfi)
        iv = num(r.get("intervalo_s"))
        if iv is not None:
            d["intervalos"].add(iv)
        if d["intervalo"] is None:
            d["intervalo"] = iv
        t = num(r.get("t_s"))
        if t is not None:
            d["t_min"] = t if d["t_min"] is None else min(d["t_min"], t)
            d["t_max"] = t if d["t_max"] is None else max(d["t_max"], t)

    linhas = []
    print("=" * 104)
    print("ENSAIO DE CAPACIDADE — LoRa")
    print("=" * 104)
    print("%d canais  |  taxa de entrega exigida do pior no: %.0f%%" % (a.canais, a.pdr_alvo*100))

    limite_ok = None
    for rod in sorted(rodadas, key=lambda x: int(x) if str(x).isdigit() else 0):
        d = rodadas[rod]
        nos_validos = {n: v for n, v in d["por_no"].items() if v[1] >= a.min_pacotes}
        if not nos_validos:
            continue
        n_nos = len(nos_validos)
        dur = (d["t_max"] - d["t_min"]) if (d["t_max"] is not None and d["t_min"] is not None) else None
        env = sum(v[1] for v in nos_validos.values())
        rec = sum(v[0] for v in nos_validos.values())
        pdr_agr = rec/env if env else 0.0

        # carga oferecida por canal, em erlangs
        G = (d["airtime"]/(dur*a.canais)) if dur else None

        por_no = {n: (v[0]/v[1]) for n, v in nos_validos.items()}
        pior_no = min(por_no, key=lambda n: por_no[n])
        pior = por_no[pior_no]
        j = jain(list(por_no.values()))

        por_classe = defaultdict(lambda: [0, 0])
        for n, v in nos_validos.items():
            c = d["classe_do_no"].get(n, "?")
            por_classe[c][0] += v[0]
            por_classe[c][1] += v[1]

        misto = len(d["intervalos"]) > 1
        rot_iv = ("misto: " + "/".join("%.0f" % x for x in sorted(d["intervalos"])) + " s"
                  if misto else "intervalo %.0f s" % (d["intervalo"] or 0))
        print("\n--- rodada %s: %d nos, %s ---" % (rod, n_nos, rot_iv))
        print("carga oferecida por canal: %s erlang   |   entrega agregada: %.1f%%"
              % (("%.3f" % G) if G else "?", pdr_agr*100))
        print("%-10s %6s %9s %9s %18s" % ("classe", "nos", "pacotes", "entrega", "IC 95%"))
        classe_critica = None
        for c in sorted(por_classe, key=lambda x: ORDEM_CLASSE.get(x, 9)):
            rc, ec = por_classe[c]
            n_c = sum(1 for n in nos_validos if d["classe_do_no"].get(n) == c)
            lo, hi = wilson(rc, ec)
            print("%-10s %6d %9d %8.1f%% %8.1f%% a %5.1f%%  %s"
                  % (c, n_c, ec, 100.0*rc/ec if ec else 0, lo*100, hi*100,
                     "#" * int(round(rc/ec*20)) if ec else ""))
            if ORDEM_CLASSE.get(c, 9) == 3:
                classe_critica = (rc, ec, lo, hi)

        rec_p, tot_p = nos_validos[pior_no]
        lo_p, hi_p = wilson(rec_p, tot_p)
        print("pior no: %s com %.1f%% (IC 95%%: %.1f%% a %.1f%%, n=%d)   |   Jain: %.3f"
              % (pior_no, pior*100, lo_p*100, hi_p*100, tot_p, j or 0))
        n_min = n_para_precisao(a.pdr_alvo, 0.05)
        if tot_p < n_min:
            print("  amostra pequena: %d pacotes no pior no. Para decidir contra %.0f%% com"
                  % (tot_p, a.pdr_alvo*100))
            print("  +/- 5 pontos sao necessarios ~%d pacotes -- ou seja, rodada de %.0f min"
                  % (n_min, n_min*(min(d["intervalos"]) if d["intervalos"] else 10)/60.0))
        if lo_p >= a.pdr_alvo:
            print("VEREDITO: passa — o pior no fica acima de %.0f%% com 95%% de confianca"
                  % (a.pdr_alvo*100))
            limite_ok = (n_nos, rot_iv)
        elif hi_p < a.pdr_alvo:
            print("VEREDITO: REPROVA — o pior no fica abaixo de %.0f%% com 95%% de confianca"
                  % (a.pdr_alvo*100))
        else:
            print("VEREDITO: indefinido — o intervalo de confianca cruza os %.0f%%. Rodada mais longa."
                  % (a.pdr_alvo*100))
        if classe_critica and classe_critica[1] > 0:
            rc, ec, lo_c, hi_c = classe_critica
            if hi_c < a.pdr_alvo:
                print("  a classe 'limite' -- o praticante mais distante -- ficou em %.1f%%"
                      % (100.0*rc/ec))
                print("  enquanto a media do sistema era %.1f%%. E ele quem o sistema existe para ouvir."
                      % (pdr_agr*100))

        linhas.append({"ic_lo": lo_p, "ic_hi": hi_p,
                       "rodada": rod, "n_nos": n_nos, "intervalo_s": d["intervalo"],
                       "carga_erlang": round(G, 4) if G else "",
                       "pdr_agregada": round(pdr_agr, 4),
                       "pdr_pior_no": round(pior, 4), "pior_no": pior_no,
                       "jain": round(j, 4) if j else ""})

    print("\n" + "=" * 104)
    print("RESUMO")
    print("=" * 104)
    print("%8s %6s %10s %11s %11s %20s %7s" %
          ("rodada", "nos", "carga", "agregada", "pior no", "IC do pior no", "Jain"))
    for l in linhas:
        print("%8s %6d %10s %10.1f%% %10.1f%% %9.1f%% a %6.1f%% %7s" %
              (l["rodada"], l["n_nos"], l["carga_erlang"], l["pdr_agregada"]*100,
               l["pdr_pior_no"]*100, l["ic_lo"]*100, l["ic_hi"]*100, l["jain"]))

    if limite_ok:
        print("\nCAPACIDADE MEDIDA: %d praticantes (%s), com o pior no acima de %.0f%%."
              % (limite_ok[0], limite_ok[1], a.pdr_alvo*100))
    else:
        print("\nCAPACIDADE MEDIDA: nenhuma rodada passou. Aumentar o intervalo,")
        print("reduzir o SF dos nos proximos ou acrescentar canais.")

    # onde a diferenca entre agregada e pior no abre
    for l in linhas:
        fosso = l["pdr_agregada"] - l["pdr_pior_no"]
        if fosso > 0.15:
            print("\nA partir de %d nos a media deixa de representar o sistema:" % l["n_nos"])
            print("agregada %.1f%% contra %.1f%% do pior no — %.0f pontos de diferenca."
                  % (l["pdr_agregada"]*100, l["pdr_pior_no"]*100, fosso*100))
            print("Relatar capacidade pela agregada, aqui, seria esconder a falha.")
            break

    with open(a.saida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["rodada", "n_nos", "intervalo_s", "carga_erlang",
                                           "pdr_agregada", "pdr_pior_no", "ic_lo", "ic_hi",
                                           "pior_no", "jain"], extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow(l)
    print("\nresultados em %s" % a.saida)

if __name__ == "__main__":
    main()
