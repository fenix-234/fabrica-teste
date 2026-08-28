#!/usr/bin/env python3
"""
Estima ate onde o sinal celular alcanca no mar, a partir de cada spot.

Entrada obrigatoria: o CSV de estacoes licenciadas do Servico Movel Pessoal
publicado pela ANATEL em dados.gov.br (dataset "Estacoes Licenciadas a operar
no Servico Movel Pessoal"). O arquivo nao acompanha este repositorio: baixe,
filtre pelos municipios do litoral e aponte com --erb.

Saidas: um CSV com o diagnostico por spot e um GeoJSON com os pontos e os
circulos de alcance, para abrir no QGIS ou em qualquer visualizador de mapa.

Sem dependencias externas: apenas a biblioteca padrao.
"""

import argparse, csv, json, math, sys
from collections import namedtuple

R_TERRA = 6371000.0
K_REFRACAO = 4.0 / 3.0          # raio efetivo da Terra em atmosfera padrao
C_LUZ = 299.792458              # m * MHz

Erb = namedtuple("Erb", "lat lon altura freq operadora tecnologia")

# ---------------------------------------------------------------- geometria

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R_TERRA * math.asin(math.sqrt(a)) / 1000.0

def destino_km(lat, lon, azimute_deg, dist_km):
    ad = dist_km*1000.0/R_TERRA
    th = math.radians(azimute_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1)*math.cos(ad) + math.cos(p1)*math.sin(ad)*math.cos(th))
    l2 = l1 + math.atan2(math.sin(th)*math.sin(ad)*math.cos(p1),
                         math.cos(ad) - math.sin(p1)*math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180

# ---------------------------------------------------------------- radio

def horizonte_km(ht_m, hr_m):
    return (math.sqrt(2*K_REFRACAO*R_TERRA*ht_m) +
            math.sqrt(2*K_REFRACAO*R_TERRA*hr_m)) / 1000.0

def orcamento_db(eirp_total_dbm, n_rb, rsrp_alvo_dbm, perda_corpo_db, margem_db):
    eirp_re = eirp_total_dbm - 10*math.log10(12*n_rb)
    return eirp_re - rsrp_alvo_dbm - perda_corpo_db - margem_db

def alcance_espaco_livre_km(orcamento, f_mhz):
    return 10 ** ((orcamento - 32.44 - 20*math.log10(f_mhz)) / 20)

def alcance_dois_raios_km(orcamento, ht_m, hr_m):
    x = (orcamento + 20*math.log10(ht_m) + 20*math.log10(hr_m)) / 40
    return (10 ** x) / 1000.0

def breakpoint_km(ht_m, hr_m, f_mhz):
    return (4*ht_m*hr_m / (C_LUZ/f_mhz)) / 1000.0

def alcance_erb(erb, cfg):
    """Retorna (dois_raios, espaco_livre, horizonte, pratico) em km."""
    ht = max(erb.altura, 5.0)
    hr = cfg["h_usuario"]
    orc = orcamento_db(cfg["eirp"], cfg["n_rb"], cfg["rsrp"],
                       cfg["perda_corpo"], cfg["margem"])
    dr = alcance_dois_raios_km(orc, ht, hr)
    el = alcance_espaco_livre_km(orc, erb.freq)
    hz = horizonte_km(ht, hr)
    teto = min(el, hz)
    pratico = min(dr * cfg["fator_calibracao"], teto)
    return dr, el, hz, pratico

# ---------------------------------------------------------------- leitura

ALIAS_LAT  = ("latitude", "latdecimal", "lat", "latitudedecimal")
ALIAS_LON  = ("longitude", "longdecimal", "lon", "lng", "longitudedecimal")
ALIAS_ALT  = ("alturaantena", "altura", "alturaestacao", "heightantenna")
ALIAS_FREQ = ("freqtxmhz", "frequenciatransmissao", "freqtx", "frequencia")
ALIAS_OPER = ("nomeentidade", "entidade", "operadora", "razaosocial")
ALIAS_TEC  = ("tecnologia", "tecnologiatransmissao", "designacaoemissao")

def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())

def _achar(cabecalho, aliases):
    mapa = {_norm(c): c for c in cabecalho}
    for a in aliases:
        if a in mapa:
            return mapa[a]
    return None

def _num(v, padrao=None):
    if v is None:
        return padrao
    v = str(v).strip().replace(",", ".")
    if not v:
        return padrao
    try:
        return float(v)
    except ValueError:
        return padrao

def ler_erbs(caminho, altura_padrao, freq_padrao, delim=None):
    with open(caminho, newline="", encoding="utf-8", errors="replace") as fh:
        amostra = fh.read(8192); fh.seek(0)
        if delim is None:
            try:
                delim = csv.Sniffer().sniff(amostra, delimiters=";,|\t").delimiter
            except csv.Error:
                delim = ";"
        leitor = csv.DictReader(fh, delimiter=delim)
        cab = leitor.fieldnames or []
        c_lat, c_lon = _achar(cab, ALIAS_LAT), _achar(cab, ALIAS_LON)
        if not c_lat or not c_lon:
            sys.exit("ERRO: nao encontrei colunas de latitude/longitude em %s\n"
                     "Colunas vistas: %s" % (caminho, ", ".join(cab[:25])))
        c_alt  = _achar(cab, ALIAS_ALT)
        c_freq = _achar(cab, ALIAS_FREQ)
        c_oper = _achar(cab, ALIAS_OPER)
        c_tec  = _achar(cab, ALIAS_TEC)
        out = []
        for linha in leitor:
            lat, lon = _num(linha.get(c_lat)), _num(linha.get(c_lon))
            if lat is None or lon is None or (lat == 0 and lon == 0):
                continue
            if not (-35 <= lat <= 6 and -75 <= lon <= -32):
                continue
            out.append(Erb(
                lat, lon,
                _num(linha.get(c_alt) if c_alt else None, altura_padrao) or altura_padrao,
                _num(linha.get(c_freq) if c_freq else None, freq_padrao) or freq_padrao,
                (linha.get(c_oper) or "").strip() if c_oper else "",
                (linha.get(c_tec) or "").strip() if c_tec else "",
            ))
        return out

def ler_spots(caminho):
    with open(caminho, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh)]

# ---------------------------------------------------------------- analise

def classificar(pratico_km, n_erbs):
    if n_erbs == 0 or pratico_km <= 0:
        return "SEM COBERTURA"
    if pratico_km < 2:   return "CRITICO"
    if pratico_km < 5:   return "LIMITADO"
    if pratico_km < 10:  return "ACEITAVEL"
    return "BOM"

def analisar_spot(spot, erbs, cfg):
    lat, lon = float(spot["lat"]), float(spot["lon"])
    perto = []
    for e in erbs:
        d = haversine_km(lat, lon, e.lat, e.lon)
        if d <= cfg["raio_busca"]:
            perto.append((d, e))
    perto.sort(key=lambda x: x[0])

    melhor = 0.0; melhor_erb = None; detalhe = None
    for d, e in perto:
        dr, el, hz, pratico = alcance_erb(e, cfg)
        # alcance util a partir da praia = alcance da ERB menos a distancia
        # que ela ja gasta para chegar ate a linha d'agua
        util = pratico - d
        if util > melhor:
            melhor, melhor_erb, detalhe = util, e, (dr, el, hz, pratico, d)

    return {
        "id": spot["id"], "nome": spot["nome"], "uf": spot["uf"],
        "lat": lat, "lon": lon,
        "tipo": spot.get("tipo", ""), "prior": spot.get("prior", ""),
        "n_erbs_raio": len(perto),
        "erb_mais_proxima_km": round(perto[0][0], 2) if perto else None,
        "alcance_mar_km": round(max(melhor, 0.0), 2),
        "classe": classificar(melhor, len(perto)),
        "operadora_dominante": melhor_erb.operadora if melhor_erb else "",
        "freq_mhz": melhor_erb.freq if melhor_erb else None,
        "altura_torre_m": melhor_erb.altura if melhor_erb else None,
        "_detalhe": detalhe,
    }

def analisar_corredor(a, b, erbs, cfg, passo_km=2.0):
    """Amostra a linha entre dois spots e devolve o pior trecho — é no corredor
    de downwind, não na praia de largada, que o rastreio some."""
    lat1, lon1 = float(a["lat"]), float(a["lon"])
    lat2, lon2 = float(b["lat"]), float(b["lon"])
    total = haversine_km(lat1, lon1, lat2, lon2)
    if total < passo_km:
        return []
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon)*math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1))*math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1))*math.cos(math.radians(lat2))*math.cos(dlon))
    azim = (math.degrees(math.atan2(y, x)) + 360) % 360
    pontos = []
    d = 0.0
    while d <= total:
        plat, plon = destino_km(lat1, lon1, azim, d)
        r = analisar_spot({"id": "corr", "nome": "%.0f km" % d, "uf": a["uf"],
                           "lat": plat, "lon": plon}, erbs, cfg)
        pontos.append((round(d, 1), plat, plon, r["alcance_mar_km"], r["classe"]))
        d += passo_km
    return pontos

# ---------------------------------------------------------------- saida

def circulo_geojson(lat, lon, raio_km, n=48):
    return [[destino_km(lat, lon, 360.0*i/n, raio_km)[1],
             destino_km(lat, lon, 360.0*i/n, raio_km)[0]] for i in range(n+1)]

def escrever_geojson(caminho, resultados):
    feats = []
    for r in resultados:
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": {k: v for k, v in r.items() if not k.startswith("_")}})
        if r["alcance_mar_km"] > 0:
            feats.append({"type": "Feature",
                          "geometry": {"type": "Polygon",
                                       "coordinates": [circulo_geojson(r["lat"], r["lon"], r["alcance_mar_km"])]},
                          "properties": {"id": r["id"], "nome": r["nome"],
                                         "classe": r["classe"], "raio_km": r["alcance_mar_km"]}})
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False)

# ---------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--erb", required=True, help="CSV de estacoes licenciadas da ANATEL")
    p.add_argument("--spots", required=True, help="CSV de spots (ver spots_brasil.csv)")
    p.add_argument("--saida-csv", default="cobertura_spots.csv")
    p.add_argument("--saida-geojson", default="cobertura_spots.geojson")
    p.add_argument("--corredor", help="ID_A,ID_B para analisar o trecho de downwind entre dois spots")
    p.add_argument("--delimitador", help="delimitador do CSV da ANATEL (padrao: detectado)")

    p.add_argument("--h-usuario", type=float, default=0.8,
                   help="altura da antena do praticante acima da agua, em m (padrao 0.8)")
    p.add_argument("--eirp", type=float, default=60.0, help="EIRP total da ERB em dBm")
    p.add_argument("--n-rb", type=int, default=100, help="resource blocks (100 = 20 MHz)")
    p.add_argument("--rsrp", type=float, default=-110.0, help="RSRP alvo em dBm")
    p.add_argument("--perda-corpo", type=float, default=10.0,
                   help="perda por corpo, bolsa estanque e imersao, em dB")
    p.add_argument("--margem", type=float, default=8.0, help="margem de sombreamento em dB")
    p.add_argument("--fator-calibracao", type=float, default=1.5,
                   help="fator sobre o modelo de 2 raios; 1.5 reproduz os ~8 km medidos "
                        "em torre de 30 m a 700 MHz. Reajuste com os dados de campo.")
    p.add_argument("--raio-busca", type=float, default=60.0,
                   help="raio de busca de ERBs ao redor do spot, em km")
    p.add_argument("--altura-padrao", type=float, default=30.0,
                   help="altura assumida quando a ANATEL nao informa")
    p.add_argument("--freq-padrao", type=float, default=850.0,
                   help="frequencia assumida quando a ANATEL nao informa")
    a = p.parse_args()

    cfg = {"h_usuario": a.h_usuario, "eirp": a.eirp, "n_rb": a.n_rb, "rsrp": a.rsrp,
           "perda_corpo": a.perda_corpo, "margem": a.margem,
           "fator_calibracao": a.fator_calibracao, "raio_busca": a.raio_busca}

    erbs = ler_erbs(a.erb, a.altura_padrao, a.freq_padrao, a.delimitador)
    spots = ler_spots(a.spots)
    print("ERBs carregadas: %d  |  spots: %d" % (len(erbs), len(spots)), file=sys.stderr)
    if not erbs:
        sys.exit("ERRO: nenhuma ERB valida no arquivo informado.")

    res = [analisar_spot(s, erbs, cfg) for s in spots]
    res.sort(key=lambda r: r["alcance_mar_km"])

    campos = ["id", "nome", "uf", "classe", "alcance_mar_km", "n_erbs_raio",
              "erb_mais_proxima_km", "altura_torre_m", "freq_mhz",
              "operadora_dominante", "tipo", "prior", "lat", "lon"]
    with open(a.saida_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in res:
            w.writerow(r)
    escrever_geojson(a.saida_geojson, res)

    print("\n%-28s %-3s %-14s %9s %7s" % ("SPOT", "UF", "CLASSE", "MAR(km)", "ERBs"))
    print("-" * 68)
    for r in res:
        print("%-28s %-3s %-14s %9.2f %7d" % (r["nome"][:28], r["uf"], r["classe"],
                                              r["alcance_mar_km"], r["n_erbs_raio"]))
    ruins = [r for r in res if r["classe"] in ("SEM COBERTURA", "CRITICO")]
    print("\n%d spot(s) sem cobertura util no mar." % len(ruins))
    print("CSV: %s   GeoJSON: %s" % (a.saida_csv, a.saida_geojson))

    if a.corredor:
        ida, idb = [x.strip() for x in a.corredor.split(",")]
        sa = next((s for s in spots if s["id"] == ida), None)
        sb = next((s for s in spots if s["id"] == idb), None)
        if not sa or not sb:
            sys.exit("ERRO: id de spot nao encontrado no corredor.")
        print("\nCORREDOR %s -> %s" % (sa["nome"], sb["nome"]))
        print("%8s %10s %14s" % ("km", "mar(km)", "classe"))
        for d, plat, plon, alc, cl in analisar_corredor(sa, sb, erbs, cfg):
            print("%8.1f %10.2f %14s" % (d, alc, cl))

if __name__ == "__main__":
    main()
