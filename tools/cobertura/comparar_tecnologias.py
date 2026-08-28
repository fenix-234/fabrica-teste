#!/usr/bin/env python3
"""
Compara tecnologias de enlace para monitoramento em tempo real sobre o mar.

Usa o mesmo modelo de dois raios e horizonte de radio ja validado em
tests/test_fisica.py, aplicado a cada tecnologia com seus proprios parametros
de potencia, sensibilidade e antena.

Roda sozinho, sem dados externos:  python3 comparar_tecnologias.py
"""
import math

R = 6371000.0
K = 4.0/3.0

def horizonte_km(ht, hr):
    return (math.sqrt(2*K*R*ht) + math.sqrt(2*K*R*hr))/1000.0

def d_dois_raios_km(orc_db, ht, hr):
    return (10 ** ((orc_db + 20*math.log10(ht) + 20*math.log10(hr))/40))/1000.0

def d_espaco_livre_km(orc_db, f_mhz):
    return 10 ** ((orc_db - 32.44 - 20*math.log10(f_mhz))/20)

def alcance(orc_db, ht, hr, f_mhz):
    dr = d_dois_raios_km(orc_db, ht, hr)
    return dr, min(d_espaco_livre_km(orc_db, f_mhz), horizonte_km(ht, hr))

# ------------------------------------------------------------------ cenario
H_USUARIO   = 0.8     # antena do praticante acima da agua
PERDA_CORPO = 10.0    # corpo molhado + bolsa estanque
MARGEM      = 10.0    # sombreamento por onda

def linha(nome, orc, ht, f, obs=""):
    dr, teto = alcance(orc, ht, H_USUARIO, f)
    pratico = min(dr*1.5, teto)
    limite = "horizonte" if teto <= d_espaco_livre_km(orc, f) else "espaco livre"
    if pratico >= teto - 0.01:
        limite = "LIMITADO PELO HORIZONTE"
    else:
        limite = "limitado pelo orcamento"
    print("%-34s %7.1f %9.1f %9.1f %9.1f   %-24s %s"
          % (nome, orc, dr, pratico, teto, limite, obs))

print("=" * 132)
print("ALCANCE SOBRE O MAR — praticante a %.1f m, perda de corpo %.0f dB, margem %.0f dB"
      % (H_USUARIO, PERDA_CORPO, MARGEM))
print("=" * 132)
print("%-34s %7s %9s %9s %9s   %-24s %s"
      % ("tecnologia / cenario", "orc dB", "2raios", "pratico", "teto", "o que limita", "obs"))
print("-" * 132)

# --- LTE (referencia do levantamento anterior)
eirp_re = 60 - 10*math.log10(12*100)          # 20 MHz
orc_lte = eirp_re - (-110) - PERDA_CORPO - 8  # margem 8 usada no estudo anterior
linha("LTE 700 MHz, torre 30 m", orc_lte, 30, 700)
linha("LTE 700 MHz, torre 60 m", orc_lte, 60, 700)
linha("LTE 700 MHz, torre 100 m", orc_lte, 100, 700)

print()
# --- LoRa: no -> gateway. ANATEL Ato 14448: ate 30 dBm com >=35 canais de salto
SENS = {"SF7": -125.0, "SF9": -131.0, "SF10": -133.0, "SF12": -139.0}
TX_NO   = 20.0   # conduzido no vestivel
G_NO    = -2.0   # antena pequena junto ao corpo
G_GW    = 6.0
for sf in ("SF7", "SF10", "SF12"):
    orc = (TX_NO + G_NO - PERDA_CORPO) + G_GW - SENS[sf] - MARGEM
    linha("LoRa %s, gateway 30 m" % sf, orc, 30, 915)
for sf in ("SF10", "SF12"):
    orc = (TX_NO + G_NO - PERDA_CORPO) + G_GW - SENS[sf] - MARGEM
    linha("LoRa %s, gateway 60 m" % sf, orc, 60, 915)

print()
# --- elevar o gateway: duna, morro, mastro alto, drone cativo, balao
for alt, rot in ((100, "duna/morro 100 m"), (120, "drone cativo 120 m"), (300, "balao cativo 300 m")):
    orc = (TX_NO + G_NO - PERDA_CORPO) + G_GW - SENS["SF12"] - MARGEM
    linha("LoRa SF12, %s" % rot, orc, alt, 915)
    orc10 = (TX_NO + G_NO - PERDA_CORPO) + G_GW - SENS["SF10"] - MARGEM
    linha("LoRa SF10, %s" % rot, orc10, alt, 915)
linha("LTE 700 MHz, drone cativo 120 m", orc_lte, 120, 700, "orcamento nao acompanha a altura")

print()
# --- LoRa no -> no (malha entre praticantes): as duas pontas na agua
for sf in ("SF10", "SF12"):
    orc = (TX_NO + G_NO - PERDA_CORPO) + (G_NO - PERDA_CORPO) - SENS[sf] - MARGEM
    dr, teto = alcance(orc, H_USUARIO, H_USUARIO, 915)
    print("%-34s %7.1f %9.1f %9.1f %9.1f   %-24s %s"
          % ("LoRa %s, praticante->praticante" % sf, orc, dr, min(dr*1.5, teto), teto,
             "limitado pelo orcamento", "malha so funciona em pelotao"))

print()
# --- AIS-MOB -> estacao costeira (VHF 162 MHz, 2 W)
orc_ais = (33.0 + 0.0 - PERDA_CORPO) + G_GW - (-107.0) - MARGEM
linha("AIS-MOB -> estacao 30 m", orc_ais, 30, 162, "publicado: ~5 NM = 9,3 km")
linha("AIS-MOB -> estacao 60 m", orc_ais, 60, 162)

print()
# --- Wi-Fi HaLow 802.11ah 915 MHz
orc_halow = (23.0 - 2.0 - PERDA_CORPO) + 6.0 - (-98.0) - MARGEM
linha("Wi-Fi HaLow 1 MHz, AP 30 m", orc_halow, 30, 915, "MCS10, 150 kbps")

print()
print("=" * 132)
print("CAPACIDADE LoRa — quantos praticantes um gateway sustenta")
print("=" * 132)

def airtime_s(sf, pl_bytes, bw_khz=125, cr=1, preamble=8, crc=1, ih=0):
    tsym = (2**sf)/(bw_khz*1000.0)
    de = 1 if (sf >= 11 and bw_khz == 125) else 0
    n = 8 + max(math.ceil((8*pl_bytes - 4*sf + 28 + 16*crc - 20*ih)/(4.0*(sf-2*de)))*(cr+4), 0)
    return ((preamble + 4.25)*tsym) + n*tsym

PL = 25            # 12 B de posicao + cabecalho LoRaWAN
CANAIS = 8
CARGA = 0.18       # ALOHA puro: vazao maxima ~18% do canal
print("payload de %d bytes, %d canais, carga maxima de ALOHA %.0f%%\n" % (PL, CANAIS, CARGA*100))
print("%-6s %10s %12s %14s %14s %14s"
      % ("SF", "airtime", "msg/s uteis", "praticantes", "praticantes", "praticantes"))
print("%-6s %10s %12s %14s %14s %14s"
      % ("", "", "", "a cada 10 s", "a cada 30 s", "a cada 60 s"))
print("-" * 78)
for sf in (7, 8, 9, 10, 11, 12):
    at = airtime_s(sf, PL)
    cap = CANAIS*CARGA/at
    print("%-6s %9.0f ms %12.1f %14.0f %14.0f %14.0f"
          % ("SF%d" % sf, at*1000, cap, cap*10, cap*30, cap*60))

print()
print("=" * 132)
print("CUSTO POR SESSAO DE 4 h — quanto custa manter o rastreio ligado")
print("=" * 132)
SESSAO_H = 4
print("%-40s %12s %14s %14s %12s"
      % ("tecnologia", "fixes/sessao", "por fix", "por sessao", "por mes*"))
print("-" * 96)

def custo(nome, intervalo_s, preco_por_fix_brl, mensal_brl=0.0, nota=""):
    n = int(SESSAO_H*3600/intervalo_s)
    ses = n*preco_por_fix_brl
    print("%-40s %12d %14s %14s %12s  %s"
          % (nome, n, "R$ %.5f" % preco_por_fix_brl, "R$ %.2f" % ses,
             "R$ %.2f" % (ses*12 + mensal_brl), nota))

custo("Celular M2M (LTE-M), fix a cada 10 s", 10, 0.0000, 12.00, "franquia cobre")
custo("LoRa proprio, fix a cada 10 s", 10, 0.0000, 0.00, "so CAPEX do gateway")
custo("Iridium SBD, fix a cada 5 min", 300, 0.30, 90.00, "US$ 0,05/msg")
custo("Iridium SBD, fix a cada 10 s", 10, 0.30, 90.00, "inviavel")
custo("NB-IoT NTN, fix a cada 10 s", 10, 0.00027, 60.00, "US$ 1/MB, 50 B/fix")
print("* 12 sessoes por mes, mais a mensalidade da conectividade.")

print()
print("=" * 132)
print("MALHA ENTRE PRATICANTES — probabilidade de ter um vizinho ao alcance")
print("=" * 132)
def p_vizinho(n_riders, area_km2, raio_km):
    lam = n_riders/float(area_km2)
    return 1 - math.exp(-lam*math.pi*raio_km**2)
print("%-42s %14s %14s" % ("cenario", "alcance 1 km", "alcance 2 km"))
print("-" * 72)
for n, a, rot in ((30, 5.0, "30 praticantes num pico de 5 km2"),
                  (10, 5.0, "10 praticantes num pico de 5 km2"),
                  (3, 5.0, "3 praticantes num pico de 5 km2"),
                  (1, 5.0, "praticante sozinho, derivando")):
    if n <= 1:
        print("%-42s %13s %14s" % (rot, "0%", "0%"))
    else:
        print("%-42s %13.1f%% %13.1f%%" % (rot, 100*p_vizinho(n-1, a, 1.0), 100*p_vizinho(n-1, a, 2.0)))
