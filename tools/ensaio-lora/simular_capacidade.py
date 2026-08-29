#!/usr/bin/env python3
"""
Simula o ensaio de capacidade: N nos transmitindo contra um gateway, com
colisao, efeito de captura e limite de demoduladores paralelos.

Serve para dimensionar o ensaio antes de compra-lo (quantos nos, quais
intervalos, quantas rodadas) e para ensaiar a analise.

ATENCAO: dados simulados. Nao sao medicao.

  python3 simular_capacidade.py --saida-dir /tmp/cap
"""
import argparse, csv, math, os, random

# --------------------------------------------------------------- LoRa

def airtime_s(sf, pl_bytes=25, bw_khz=125, cr=1, preamble=8, crc=1, ih=0):
    tsym = (2**sf)/(bw_khz*1000.0)
    de = 1 if (sf >= 11 and bw_khz == 125) else 0
    n = 8 + max(math.ceil((8*pl_bytes - 4*sf + 28 + 16*crc - 20*ih)/(4.0*(sf-2*de)))*(cr+4), 0)
    return ((preamble + 4.25)*tsym) + n*tsym

SENS = {7: -125.0, 8: -128.0, 9: -131.0, 10: -133.0, 11: -136.0, 12: -139.0}

def rssi_de(dist_km, ht=30.0, hr=0.8, eirp=14.0):
    d = max(dist_km*1000.0, 1.0)
    return eirp - (40*math.log10(d) - 20*math.log10(ht) - 20*math.log10(hr))

# --------------------------------------------------------------- classes

# (rotulo, distancia km, SF que o ADR escolheria)
CLASSES = [
    ("perto",  1.0,  7),
    ("medio",  6.0,  9),
    ("longe", 14.0, 10),
    ("limite",22.0, 12),
]

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--saida-dir", default=".")
    p.add_argument("--canais", type=int, default=8)
    p.add_argument("--demoduladores", type=int, default=8,
                   help="pacotes simultaneos que o gateway consegue demodular (SX1302: 8)")
    p.add_argument("--captura-db", type=float, default=6.0,
                   help="diferenca de potencia que faz o pacote mais forte sobreviver a colisao")
    p.add_argument("--duracao-s", type=float, default=600.0, help="duracao de cada rodada")
    p.add_argument("--nos", type=int, nargs="+", default=[5, 10, 20, 30, 45, 60],
                   help="numero de nos em cada rodada")
    p.add_argument("--intervalo-s", type=float, default=10.0, help="intervalo de envio por no")
    p.add_argument("--ortogonalidade", type=float, default=0.95,
                   help="fracao de colisoes entre SF diferentes que NAO se destroem")
    p.add_argument("--intervalo-por-classe", nargs=4, type=float, metavar=("PERTO","MEDIO","LONGE","LIMITE"),
                   help="intervalo de envio por classe de distancia, em s. O praticante longe "
                        "precisa de atualizacao frequente; quem esta na beira, nao")
    p.add_argument("--canais-lentos", type=int, default=0,
                   help="quantos canais reservar para SF11 e SF12 (0 = sem reserva)")
    p.add_argument("--canal-dedicado-lento", action="store_true",
                   help="reserva um canal exclusivo para SF11 e SF12, separando o no "
                        "distante da disputa com os nos fortes perto da praia")
    p.add_argument("--seed", type=int, default=11)
    a = p.parse_args()

    rng = random.Random(a.seed)
    os.makedirs(a.saida_dir, exist_ok=True)
    fn_nos = os.path.join(a.saida_dir, "nos.csv")
    fn_gw  = os.path.join(a.saida_dir, "gateway.csv")
    wn = csv.writer(open(fn_nos, "w", newline="", encoding="utf-8"))
    wg = csv.writer(open(fn_gw,  "w", newline="", encoding="utf-8"))
    wn.writerow(["rodada", "t_s", "no_id", "seq", "sf", "canal", "classe", "intervalo_s"])
    wg.writerow(["rodada", "t_s", "no_id", "seq", "sf", "canal", "rssi_dbm", "snr_db"])

    for rodada, n_nos in enumerate(a.nos, start=1):
        # distribui os nos pelas classes, mantendo a proporcao realista:
        # a maioria fica perto, poucos vao ao limite
        pesos = [0.45, 0.30, 0.18, 0.07]
        nos = []
        for i in range(n_nos):
            r = rng.random(); acc = 0.0; ci = 0
            for k, w in enumerate(pesos):
                acc += w
                if r <= acc:
                    ci = k; break
            rot, dist, sf = CLASSES[ci]
            intervalo = a.intervalo_por_classe[ci] if a.intervalo_por_classe else a.intervalo_s
            nos.append({"id": "N%02d" % i, "classe": rot, "sf": sf, "intervalo": intervalo,
                        "rssi": rssi_de(dist) + rng.gauss(0, 3.0)})

        # gera todas as transmissoes da rodada
        n_lentos = a.canais_lentos or (1 if a.canal_dedicado_lento else 0)
        tx = []
        for no in nos:
            t = rng.uniform(0, no["intervalo"])
            seq = 0
            at = airtime_s(no["sf"])
            while t < a.duracao_s:
                if n_lentos > 0:
                    canal = (rng.randrange(n_lentos) if no["sf"] >= 11
                             else n_lentos + rng.randrange(a.canais - n_lentos))
                else:
                    canal = rng.randrange(a.canais)
                tx.append({"t": t, "dur": at, "no": no, "seq": seq, "canal": canal})
                wn.writerow([rodada, "%.3f" % t, no["id"], seq, "SF%d" % no["sf"],
                             canal, no["classe"], no["intervalo"]])
                seq += 1
                t += no["intervalo"]*rng.uniform(0.9, 1.1)   # jitter
        tx.sort(key=lambda x: x["t"])

        # decide o que o gateway recebe
        for i, pkt in enumerate(tx):
            if pkt["no"]["rssi"] < SENS[pkt["no"]["sf"]]:
                continue                                    # abaixo da sensibilidade
            fim = pkt["t"] + pkt["dur"]
            simultaneos = []
            for j in range(max(0, i-400), min(len(tx), i+400)):
                if j == i:
                    continue
                o = tx[j]
                if o["t"] < fim and o["t"] + o["dur"] > pkt["t"]:
                    simultaneos.append(o)

            # limite de demoduladores paralelos
            if len(simultaneos) >= a.demoduladores:
                continue

            perdeu = False
            for o in simultaneos:
                if o["canal"] != pkt["canal"]:
                    continue
                if o["no"]["sf"] != pkt["no"]["sf"] and rng.random() < a.ortogonalidade:
                    continue                                # SFs quase ortogonais
                # mesma faixa e mesmo SF: sobrevive so quem for bem mais forte
                if pkt["no"]["rssi"] < o["no"]["rssi"] + a.captura_db:
                    perdeu = True
                    break
            if perdeu:
                continue

            r = pkt["no"]["rssi"] + rng.gauss(0, 1.0)
            wg.writerow([rodada, "%.3f" % pkt["t"], pkt["no"]["id"], pkt["seq"],
                         "SF%d" % pkt["no"]["sf"], pkt["canal"], "%.1f" % r,
                         "%.1f" % (r - SENS[pkt["no"]["sf"]] - 10)])

        print("rodada %d: %d nos, %d transmissoes" % (rodada, n_nos, len(tx)))

    print("\nnos:     %s\ngateway: %s" % (fn_nos, fn_gw))

if __name__ == "__main__":
    main()
