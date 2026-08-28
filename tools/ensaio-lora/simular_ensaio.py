#!/usr/bin/env python3
"""
Gera dados SINTETICOS de um ensaio de alcance LoRa, no formato exato que o
gateway e o no vao produzir em campo.

Serve para dois fins:
  1. ensaiar a analise antes de gastar o dia de barco -- se o pipeline quebrar,
     que quebre aqui;
  2. treinar a equipe na leitura do relatorio.

ATENCAO: os dados sao simulados a partir do modelo de dois raios com
sombreamento log-normal. Nao sao medicao.

  python3 simular_ensaio.py --saida-dir /tmp/ensaio
"""
import argparse, csv, math, os, random

R = 6371000.0
K = 4.0/3.0
SENS = {"SF7": -125.0, "SF9": -131.0, "SF10": -133.0, "SF12": -139.0}

def horizonte_km(ht, hr):
    return (math.sqrt(2*K*R*ht) + math.sqrt(2*K*R*hr))/1000.0

def destino(lat, lon, azim, dist_km):
    ad = dist_km*1000.0/R
    th = math.radians(azim)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1)*math.cos(ad) + math.cos(p1)*math.sin(ad)*math.cos(th))
    l2 = l1 + math.atan2(math.sin(th)*math.sin(ad)*math.cos(p1),
                         math.cos(ad) - math.sin(p1)*math.sin(p2))
    return math.degrees(p2), (math.degrees(l2)+540) % 360 - 180

def rssi_dbm(d_km, ht, hr, eirp_dbm, sigma, rng):
    d_m = max(d_km*1000.0, 1.0)
    pl = 40*math.log10(d_m) - 20*math.log10(ht) - 20*math.log10(hr)
    return eirp_dbm - pl + rng.gauss(0, sigma)

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--saida-dir", default=".")
    p.add_argument("--gw-lat", type=float, default=-2.7961)
    p.add_argument("--gw-lon", type=float, default=-40.5137)
    p.add_argument("--gw-altura", type=float, default=30.0)
    p.add_argument("--h-no", type=float, default=0.8)
    p.add_argument("--azimute", type=float, default=15.0, help="rumo do transecto, mar adentro")
    p.add_argument("--vel-kmh", type=float, default=22.0)
    p.add_argument("--intervalo-s", type=float, default=2.0)
    p.add_argument("--dist-max-km", type=float, default=32.0)
    p.add_argument("--sigma", type=float, default=6.0, help="sombreamento log-normal, dB")
    p.add_argument("--eirp", type=float, default=14.0, help="EIRP efetivo do no, ja com perda de corpo")
    p.add_argument("--perda-fix", type=float, default=0.02, help="fracao de amostras sem fix de GPS")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    rng = random.Random(a.seed)
    os.makedirs(a.saida_dir, exist_ok=True)
    ciclo = ["SF7", "SF9", "SF10", "SF12"]
    passo_km = a.vel_kmh*a.intervalo_s/3600.0

    fn_no = os.path.join(a.saida_dir, "no.csv")
    fn_gw = os.path.join(a.saida_dir, "gateway.csv")
    wn = csv.writer(open(fn_no, "w", newline="", encoding="utf-8"))
    wg = csv.writer(open(fn_gw, "w", newline="", encoding="utf-8"))
    wn.writerow(["ts_utc", "seq", "sf", "lat", "lon", "hdop", "sats", "bateria_v", "posicao_corpo"])
    wg.writerow(["ts_utc", "seq", "sf", "rssi_dbm", "snr_db", "freq_mhz"])

    seq = 0
    d = 0.05
    t = 0.0
    enviados = recebidos = 0
    while d <= a.dist_max_km:
        sf = ciclo[seq % len(ciclo)]
        lat, lon = destino(a.gw_lat, a.gw_lon, a.azimute, d)
        ts = "2026-09-14T%02d:%02d:%02dZ" % (11 + int(t)//3600, (int(t)//60) % 60, int(t) % 60)
        sem_fix = rng.random() < a.perda_fix
        wn.writerow([ts, seq, sf,
                     "" if sem_fix else "%.6f" % lat,
                     "" if sem_fix else "%.6f" % lon,
                     "%.1f" % rng.uniform(0.7, 1.8), rng.randint(7, 12),
                     "%.2f" % (4.1 - 0.0002*seq), "braco"])
        enviados += 1
        r = rssi_dbm(d, a.gw_altura, a.h_no, a.eirp, a.sigma, rng)
        if d <= horizonte_km(a.gw_altura, a.h_no) and r >= SENS[sf]:
            wg.writerow([ts, seq, sf, "%.1f" % r,
                         "%.1f" % (r - SENS[sf] - 10 + rng.gauss(0, 1.5)), "915.2"])
            recebidos += 1
        seq += 1
        d += passo_km
        t += a.intervalo_s

    # trecho parado a 2 km para medir perda por posicao no corpo
    lat, lon = destino(a.gw_lat, a.gw_lon, a.azimute, 2.0)
    for pos, extra in (("no ar, mastro do barco", 0.0), ("braco", -5.0),
                       ("colete", -12.0), ("submerso 10 cm", -20.0)):
        for _ in range(40):
            sf = "SF10"
            ts = "2026-09-14T13:%02d:%02dZ" % ((seq//60) % 60, seq % 60)
            wn.writerow([ts, seq, sf, "%.6f" % lat, "%.6f" % lon, "0.9", 11, "3.90", pos])
            enviados += 1
            r = rssi_dbm(2.0, a.gw_altura, a.h_no, a.eirp + extra, 3.0, rng)
            if r >= SENS[sf]:
                wg.writerow([ts, seq, sf, "%.1f" % r, "%.1f" % (r - SENS[sf] - 10), "915.2"])
                recebidos += 1
            seq += 1

    print("simulado: %d transmissoes, %d recebidas (%.0f%%)"
          % (enviados, recebidos, 100.0*recebidos/enviados))
    print("no:      %s\ngateway: %s" % (fn_no, fn_gw))

if __name__ == "__main__":
    main()
