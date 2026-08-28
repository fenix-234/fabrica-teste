#!/usr/bin/env python3
"""
Estima ate onde o sinal celular alcanca no mar, a partir de cada spot.

Entrada: o CSV de estacoes licenciadas do Servico Movel Pessoal publicado pela
ANATEL em dados.gov.br. Aceita .csv, .csv.gz e .zip diretamente.

O arquivo real tem milhoes de linhas, entao a leitura e feita em streaming com
pre-filtro por caixa envolvente: so as estacoes que podem alcancar algum spot
entram na memoria.

Quando a base traz potencia e ganho, o EIRP de cada estacao e calculado dela --
nao assumido. Quando traz azimute, o apontamento da antena e levado em conta.

Saidas: CSV com o diagnostico por spot e GeoJSON com pontos e circulos de
alcance, para abrir no QGIS.

Sem dependencias externas.
"""

import argparse, csv, gzip, io, json, math, os, re, sys, time, zipfile
from collections import namedtuple

R_TERRA = 6371000.0
K_REFRACAO = 4.0 / 3.0
C_LUZ = 299.792458          # m * MHz

Erb = namedtuple("Erb", "lat lon altura freq eirp azimute operadora tecnologia municipio uf")

# ---------------------------------------------------------------- geometria

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R_TERRA * math.asin(math.sqrt(a)) / 1000.0

def azimute_entre(lat1, lon1, lat2, lon2):
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon)*math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1))*math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1))*math.cos(math.radians(lat2))*math.cos(dlon))
    return (math.degrees(math.atan2(y, x)) + 360) % 360

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

def eirp_por_re(eirp_total_dbm, n_rb):
    return eirp_total_dbm - 10*math.log10(12*n_rb)

def alcance_espaco_livre_km(orcamento, f_mhz):
    return 10 ** ((orcamento - 32.44 - 20*math.log10(f_mhz)) / 20)

def alcance_dois_raios_km(orcamento, ht_m, hr_m):
    return (10 ** ((orcamento + 20*math.log10(ht_m) + 20*math.log10(hr_m)) / 40)) / 1000.0

def breakpoint_km(ht_m, hr_m, f_mhz):
    return (4*ht_m*hr_m / (C_LUZ/f_mhz)) / 1000.0

def atenuacao_setor_db(azim_antena, azim_alvo, cfg):
    """Antena setorial: perda quando o alvo nao esta no lobo principal."""
    if azim_antena is None or not cfg["usar_azimute"]:
        return 0.0
    d = abs((azim_alvo - azim_antena + 180) % 360 - 180)
    if d <= 60:   return 0.0
    if d <= 120:  return 12.0
    return 20.0

def alcance_erb(erb, azim_alvo, cfg):
    """(dois_raios, espaco_livre, horizonte, pratico) em km."""
    ht = min(max(erb.altura, 5.0), 200.0)
    hr = cfg["h_usuario"]
    orc = (eirp_por_re(erb.eirp, cfg["n_rb"]) - cfg["rsrp"]
           - cfg["perda_corpo"] - cfg["margem"]
           - atenuacao_setor_db(erb.azimute, azim_alvo, cfg))
    dr = alcance_dois_raios_km(orc, ht, hr)
    el = alcance_espaco_livre_km(orc, erb.freq)
    hz = horizonte_km(ht, hr)
    teto = min(el, hz)
    return dr, el, hz, min(dr * cfg["fator_calibracao"], teto)

# ---------------------------------------------------------------- leitura

ALIAS = {
    "lat":   ("latitude", "latdecimal", "lat", "latitudedecimal", "latitudedecimalgrau"),
    "lon":   ("longitude", "longdecimal", "lon", "lng", "longitudedecimal", "longitudedecimalgrau"),
    "alt":   ("alturaantena", "altura", "alturaestacao", "heightantenna"),
    "freq":  ("freqtxmhz", "frequenciatransmissao", "freqtx", "frequencia", "frequenciamhz"),
    "pot":   ("potenciatransmissorwatts", "potenciatransmissor", "potenciawatts", "potencia"),
    "ganho": ("ganhoantena", "ganho"),
    "azim":  ("azimuteantena", "azimute"),
    "oper":  ("nomeentidade", "entidade", "operadora", "razaosocial"),
    "tec":   ("tecnologia", "tecnologiatransmissao"),
    "mun":   ("municipio", "nomemunicipio", "municipionome"),
    "uf":    ("uf", "siglauf", "estado"),
}

def _sem_bom(s):
    """Remove BOM do inicio do cabecalho, tanto em UTF-8 decodificado (\ufeff)
    quanto em UTF-8 lido como latin-1 (i-trema, guillemet, ponto de interrogacao
    invertido) -- o extrato da ANATEL aparece das duas formas."""
    s = s or ""
    for bom in ("\ufeff", "\u00ef\u00bb\u00bf"):
        if s.startswith(bom):
            s = s[len(bom):]
    return s

def _norm(s):
    return "".join(ch for ch in _sem_bom(s).lower() if ch.isalnum())

def _achar(cab, chave):
    mapa = {_norm(c): c for c in cab}
    for a in ALIAS[chave]:
        if a in mapa:
            return mapa[a]
    return None

_DMS = re.compile(r"^\s*(-?\d+)[^\d\-]+(\d+)[^\d]+([\d.,]+)")

def _coord(v):
    """Aceita decimal com ponto ou virgula, e tambem grau-minuto-segundo."""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        pass
    m = _DMS.match(v)
    if m:
        g = float(m.group(1)); mi = float(m.group(2)); se = float(m.group(3).replace(",", "."))
        val = abs(g) + mi/60.0 + se/3600.0
        if g < 0 or v.strip().upper().endswith(("S", "W", "O")):
            val = -val
        return val
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

def _abrir(caminho):
    """Devolve um file-object de texto, tratando .gz e .zip."""
    if caminho.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(caminho, "rb"), encoding="utf-8", errors="replace", newline="")
    if caminho.endswith(".zip"):
        z = zipfile.ZipFile(caminho)
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not nomes:
            sys.exit("ERRO: nenhum .csv dentro de %s" % caminho)
        print("zip: usando %s" % nomes[0], file=sys.stderr)
        return io.TextIOWrapper(z.open(nomes[0]), encoding="utf-8", errors="replace", newline="")
    # tenta utf-8; cai para latin-1, comum nos extratos da ANATEL
    fh = open(caminho, "r", encoding="utf-8", errors="strict", newline="")
    try:
        fh.read(65536); fh.seek(0)
        return fh
    except UnicodeDecodeError:
        fh.close()
        print("aviso: arquivo nao e UTF-8, lendo como latin-1", file=sys.stderr)
        return open(caminho, "r", encoding="latin-1", newline="")

PASSO_CELULA = 0.25

def _celula(lat, lon):
    return (int(math.floor(lat/PASSO_CELULA)), int(math.floor(lon/PASSO_CELULA)))

def celulas_uteis(spots, raio_km):
    """Conjunto de celulas de 0,25 grau que ficam a menos de raio_km de algum
    spot. Uma caixa envolvente nao serve aqui: a lista vai do Maranhao ao Chui
    e a caixa cobriria metade do pais."""
    cells = set()
    for s in spots:
        lat, lon = float(s["lat"]), float(s["lon"])
        n = int(math.ceil(raio_km / (PASSO_CELULA*111.0*max(math.cos(math.radians(lat)), 0.2)))) + 1
        m = int(math.ceil(raio_km / (PASSO_CELULA*111.0))) + 1
        i0, j0 = _celula(lat, lon)
        for di in range(-m, m+1):
            for dj in range(-n, n+1):
                cells.add((i0+di, j0+dj))
    return cells

def ler_erbs(caminho, cfg, cells, filtro_uf=None, delim=None):
    """Streaming com pre-filtro por celula. Memoria proporcional ao numero de
    estacoes uteis, nao ao tamanho do arquivo."""
    fh = _abrir(caminho)
    amostra = fh.read(65536); fh.seek(0)
    if delim is None:
        try:
            delim = csv.Sniffer().sniff(amostra, delimiters=";,|\t").delimiter
        except csv.Error:
            delim = ";"
    print("delimitador: %r" % delim, file=sys.stderr)

    leitor = csv.DictReader(fh, delimiter=delim)
    cab = leitor.fieldnames or []
    col = {k: _achar(cab, k) for k in ALIAS}
    if not col["lat"] or not col["lon"]:
        sys.exit("ERRO: nao encontrei latitude/longitude.\nColunas: %s" % ", ".join(cab[:30]))
    print("colunas mapeadas: %s" % {k: v for k, v in col.items() if v}, file=sys.stderr)

    out = []
    total = descartadas = 0
    t0 = time.time()
    for linha in leitor:
        total += 1
        if total % 500000 == 0:
            print("  %d linhas lidas, %d estacoes uteis (%.0fs)"
                  % (total, len(out), time.time()-t0), file=sys.stderr)
        lat = _coord(linha.get(col["lat"]))
        lon = _coord(linha.get(col["lon"]))
        if lat is None or lon is None or (lat == 0 and lon == 0):
            descartadas += 1
            continue
        if _celula(lat, lon) not in cells:
            continue
        uf = (linha.get(col["uf"]) or "").strip().upper() if col["uf"] else ""
        if filtro_uf and uf and uf not in filtro_uf:
            continue

        alt = _num(linha.get(col["alt"]) if col["alt"] else None, cfg["altura_padrao"]) or cfg["altura_padrao"]
        freq = _num(linha.get(col["freq"]) if col["freq"] else None, cfg["freq_padrao"]) or cfg["freq_padrao"]
        if freq < 300 or freq > 6000:          # fora das faixas moveis usuais
            freq = cfg["freq_padrao"]

        pot = _num(linha.get(col["pot"]) if col["pot"] else None)
        ganho = _num(linha.get(col["ganho"]) if col["ganho"] else None)
        if pot and pot > 0:
            eirp = 10*math.log10(pot*1000.0) + (ganho if ganho is not None else 15.0)
            eirp = min(max(eirp, 30.0), 75.0)   # sanidade
        else:
            eirp = cfg["eirp_padrao"]

        azim = _num(linha.get(col["azim"]) if col["azim"] else None)
        if azim is not None:
            azim = azim % 360

        out.append(Erb(lat, lon, alt, freq, eirp, azim,
                       (linha.get(col["oper"]) or "").strip() if col["oper"] else "",
                       (linha.get(col["tec"]) or "").strip() if col["tec"] else "",
                       (linha.get(col["mun"]) or "").strip() if col["mun"] else "",
                       uf))
    fh.close()
    print("total de linhas: %d | dentro do alcance: %d | sem coordenada: %d | %.0fs"
          % (total, len(out), descartadas, time.time()-t0), file=sys.stderr)
    return out

def ler_spots(caminho):
    with open(caminho, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh)]

# ---------------------------------------------------------------- indice

class GradeEspacial:
    """Indice de celulas de 0,25 grau. Evita varrer todas as estacoes por spot."""
    PASSO = PASSO_CELULA

    def __init__(self, erbs):
        self.celulas = {}
        for e in erbs:
            self.celulas.setdefault(_celula(e.lat, e.lon), []).append(e)

    def proximas(self, lat, lon, raio_km):
        n = int(math.ceil(raio_km / (self.PASSO*111.0*max(math.cos(math.radians(lat)), 0.2)))) + 1
        m = int(math.ceil(raio_km / (self.PASSO*111.0))) + 1
        i0, j0 = _celula(lat, lon)
        for di in range(-m, m+1):
            for dj in range(-n, n+1):
                for e in self.celulas.get((i0+di, j0+dj), ()):
                    yield e

# ---------------------------------------------------------------- analise

def classificar(km, n):
    if n == 0 or km <= 0: return "SEM COBERTURA"
    if km < 2:  return "CRITICO"
    if km < 5:  return "LIMITADO"
    if km < 10: return "ACEITAVEL"
    return "BOM"

def analisar_ponto(lat, lon, grade, cfg):
    melhor = 0.0; melhor_erb = None; n = 0; dmin = None
    for e in grade.proximas(lat, lon, cfg["raio_busca"]):
        d = haversine_km(lat, lon, e.lat, e.lon)
        if d > cfg["raio_busca"]:
            continue
        n += 1
        if dmin is None or d < dmin:
            dmin = d
        _, _, _, pratico = alcance_erb(e, azimute_entre(e.lat, e.lon, lat, lon), cfg)
        util = pratico - d          # alcance que sobra a partir da linha d'agua
        if util > melhor:
            melhor, melhor_erb = util, e
    return melhor, melhor_erb, n, dmin

def analisar_spot(spot, grade, cfg):
    lat, lon = float(spot["lat"]), float(spot["lon"])
    melhor, erb, n, dmin = analisar_ponto(lat, lon, grade, cfg)
    return {
        "id": spot.get("id", ""), "nome": spot.get("nome", ""), "uf": spot.get("uf", ""),
        "lat": lat, "lon": lon, "tipo": spot.get("tipo", ""), "prior": spot.get("prior", ""),
        "n_erbs_raio": n,
        "erb_mais_proxima_km": round(dmin, 2) if dmin is not None else None,
        "alcance_mar_km": round(max(melhor, 0.0), 2),
        "classe": classificar(melhor, n),
        "operadora_dominante": erb.operadora if erb else "",
        "freq_mhz": round(erb.freq, 1) if erb else None,
        "altura_torre_m": round(erb.altura, 1) if erb else None,
        "eirp_dbm": round(erb.eirp, 1) if erb else None,
    }

def analisar_corredor(a, b, grade, cfg, passo_km):
    lat1, lon1 = float(a["lat"]), float(a["lon"])
    lat2, lon2 = float(b["lat"]), float(b["lon"])
    total = haversine_km(lat1, lon1, lat2, lon2)
    azim = azimute_entre(lat1, lon1, lat2, lon2)
    pontos = []
    d = 0.0
    while d <= total:
        plat, plon = destino_km(lat1, lon1, azim, d)
        melhor, _, n, _ = analisar_ponto(plat, plon, grade, cfg)
        km = round(max(melhor, 0.0), 2)
        pontos.append((round(d, 1), plat, plon, km, classificar(melhor, n)))
        d += passo_km
    return pontos

# ---------------------------------------------------------------- saida

def circulo(lat, lon, raio_km, n=48):
    pts = []
    for i in range(n+1):
        la, lo = destino_km(lat, lon, 360.0*i/n, raio_km)
        pts.append([lo, la])
    return pts

def escrever_geojson(caminho, resultados, corredor=None):
    feats = []
    for r in resultados:
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                      "properties": r})
        if r["alcance_mar_km"] > 0:
            feats.append({"type": "Feature",
                          "geometry": {"type": "Polygon", "coordinates": [circulo(r["lat"], r["lon"], r["alcance_mar_km"])]},
                          "properties": {"id": r["id"], "nome": r["nome"],
                                         "classe": r["classe"], "raio_km": r["alcance_mar_km"]}})
    if corredor:
        feats.append({"type": "Feature",
                      "geometry": {"type": "LineString",
                                   "coordinates": [[p[2], p[1]] for p in corredor]},
                      "properties": {"tipo": "corredor",
                                     "pior_km": min(p[3] for p in corredor)}})
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False)

# ---------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--erb", required=True, help="CSV/CSV.GZ/ZIP de estacoes da ANATEL")
    p.add_argument("--spots", required=True)
    p.add_argument("--saida-csv", default="cobertura_spots.csv")
    p.add_argument("--saida-geojson", default="cobertura_spots.geojson")
    p.add_argument("--corredor", help="ID_A,ID_B — perfil ao longo do downwind")
    p.add_argument("--passo-corredor", type=float, default=2.0)
    p.add_argument("--uf", help="filtra por UF, ex: CE,PI,MA")
    p.add_argument("--delimitador")

    p.add_argument("--h-usuario", type=float, default=0.8)
    p.add_argument("--eirp-padrao", type=float, default=60.0,
                   help="EIRP assumido quando a base nao traz potencia/ganho")
    p.add_argument("--n-rb", type=int, default=100)
    p.add_argument("--rsrp", type=float, default=-110.0)
    p.add_argument("--perda-corpo", type=float, default=10.0)
    p.add_argument("--margem", type=float, default=8.0)
    p.add_argument("--fator-calibracao", type=float, default=1.5)
    p.add_argument("--raio-busca", type=float, default=60.0)
    p.add_argument("--altura-padrao", type=float, default=30.0)
    p.add_argument("--freq-padrao", type=float, default=850.0)
    p.add_argument("--sem-azimute", action="store_true",
                   help="ignora o apontamento das antenas (cenario otimista)")
    a = p.parse_args()

    cfg = {"h_usuario": a.h_usuario, "eirp_padrao": a.eirp_padrao, "n_rb": a.n_rb,
           "rsrp": a.rsrp, "perda_corpo": a.perda_corpo, "margem": a.margem,
           "fator_calibracao": a.fator_calibracao, "raio_busca": a.raio_busca,
           "altura_padrao": a.altura_padrao, "freq_padrao": a.freq_padrao,
           "usar_azimute": not a.sem_azimute}

    spots = ler_spots(a.spots)
    if not spots:
        sys.exit("ERRO: lista de spots vazia.")
    cells = celulas_uteis(spots, a.raio_busca)
    print("area de interesse: %d celulas de 0,25 grau ao redor de %d spots"
          % (len(cells), len(spots)), file=sys.stderr)

    filtro_uf = set(u.strip().upper() for u in a.uf.split(",")) if a.uf else None
    erbs = ler_erbs(a.erb, cfg, cells, filtro_uf, a.delimitador)
    if not erbs:
        sys.exit("ERRO: nenhuma estacao dentro da area de interesse.")
    grade = GradeEspacial(erbs)

    t0 = time.time()
    res = [analisar_spot(s, grade, cfg) for s in spots]
    res.sort(key=lambda r: r["alcance_mar_km"])
    print("analise de %d spots em %.1fs" % (len(res), time.time()-t0), file=sys.stderr)

    campos = ["id", "nome", "uf", "classe", "alcance_mar_km", "n_erbs_raio",
              "erb_mais_proxima_km", "altura_torre_m", "freq_mhz", "eirp_dbm",
              "operadora_dominante", "tipo", "prior", "lat", "lon"]
    with open(a.saida_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in res:
            w.writerow(r)

    corr = None
    if a.corredor:
        ida, idb = [x.strip() for x in a.corredor.split(",")]
        sa = next((s for s in spots if s.get("id") == ida), None)
        sb = next((s for s in spots if s.get("id") == idb), None)
        if not sa or not sb:
            sys.exit("ERRO: id de spot nao encontrado no corredor.")
        corr = analisar_corredor(sa, sb, grade, cfg, a.passo_corredor)

    escrever_geojson(a.saida_geojson, res, corr)

    print("\n%-30s %-3s %-14s %9s %6s" % ("SPOT", "UF", "CLASSE", "MAR(km)", "ERBs"))
    print("-" * 70)
    for r in res:
        print("%-30s %-3s %-14s %9.2f %6d" % (r["nome"][:30], r["uf"], r["classe"],
                                              r["alcance_mar_km"], r["n_erbs_raio"]))
    ruins = [r for r in res if r["classe"] in ("SEM COBERTURA", "CRITICO")]
    print("\n%d de %d spot(s) sem cobertura util no mar." % (len(ruins), len(res)))
    print("CSV: %s   GeoJSON: %s" % (a.saida_csv, a.saida_geojson))

    if corr:
        print("\nCORREDOR %s -> %s" % (sa["nome"], sb["nome"]))
        print("%8s %10s %14s" % ("km", "mar(km)", "classe"))
        for d, _, _, alc, cl in corr:
            print("%8.1f %10.2f %14s" % (d, alc, cl))
        pior = min(p[3] for p in corr)
        zeros = sum(1 for p in corr if p[3] <= 0) * a.passo_corredor
        print("\npior ponto: %.2f km | %.0f km de trajeto sem cobertura" % (pior, zeros))

if __name__ == "__main__":
    main()
