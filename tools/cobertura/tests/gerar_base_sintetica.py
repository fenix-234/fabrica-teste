#!/usr/bin/env python3
"""
Gera um CSV SINTETICO com o formato do extrato de estacoes licenciadas da
ANATEL, para teste de carga do pipeline.

ATENCAO: os dados sao inventados. Serve para medir tempo, memoria e robustez
de leitura -- nunca para tirar conclusao sobre cobertura real.

Reproduz as armadilhas do arquivo verdadeiro: delimitador ';', decimal com
virgula, acentuacao em latin-1, BOM, colunas vazias e coordenadas invalidas.
"""
import csv, math, random, sys

random.seed(42)

CAB = ["NomeEntidade","NumFistel","NumServico","Latitude","Longitude","CodMunicipio",
       "Municipio","UF","Tecnologia","FreqTxMHz","FreqRxMHz","AlturaAntena",
       "GanhoAntena","PotenciaTransmissorWatts","AzimuteAntena","DataLicenciamento"]

OPERADORAS = ["TELEFONICA BRASIL S.A.","CLARO S.A.","TIM S A","ALGAR TELECOM S/A","SERCOMTEL"]
TEC  = ["LTE","NR","WCDMA","GSM"]
FREQ = [700,850,1800,1900,2100,2600,3500]
UFS  = ["MA","PI","CE","RN","PB","PE","AL","SE","BA","ES","RJ","SP","PR","SC","RS"]

def anchors_do_csv(caminho):
    out = []
    with open(caminho, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append((float(r["lat"]), float(r["lon"]), r["uf"]))
    return out

def main():
    spots_csv, saida, n_total = sys.argv[1], sys.argv[2], int(sys.argv[3])
    anchors = anchors_do_csv(spots_csv)
    n_cluster = int(n_total * 0.2)     # perto dos spots
    n_disperso = n_total - n_cluster   # resto do pais, para exercitar o filtro

    with open(saida, "w", newline="", encoding="latin-1", errors="replace") as fh:
        fh.write("﻿".encode("utf-8").decode("latin-1", "ignore"))
        w = csv.writer(fh, delimiter=";")
        w.writerow(CAB)

        def linha(lat, lon, uf):
            tec = random.choice(TEC)
            f = random.choice(FREQ)
            alt = round(random.triangular(12, 80, 30), 1)
            ganho = round(random.uniform(12, 18), 1)
            pot = round(random.choice([10, 20, 40, 60, 80]) * random.uniform(0.6, 1.3), 2)
            azim = random.choice([0, 60, 120, 180, 240, 300, ""])
            return [random.choice(OPERADORAS), random.randint(10**9, 10**10-1), 10,
                    ("%.6f" % lat).replace(".", ","), ("%.6f" % lon).replace(".", ","),
                    random.randint(1100015, 5300108), "MUNICIPIO ÁGUA BOA", uf, tec,
                    f, f-45, ("%.1f" % alt).replace(".", ","),
                    ("%.1f" % ganho).replace(".", ","), ("%.2f" % pot).replace(".", ","),
                    azim, "2026-03-14"]

        for i in range(n_cluster):
            lat, lon, uf = random.choice(anchors)
            w.writerow(linha(lat + random.gauss(0, 0.12), lon + random.gauss(0, 0.12), uf))
            if i % 200000 == 0:
                print("  cluster %d" % i, file=sys.stderr)

        for i in range(n_disperso):
            lat = random.uniform(-33.7, 4.5)
            lon = random.uniform(-73.9, -34.8)
            if i % 5000 == 0:            # sujeira proposital
                w.writerow(linha(0.0, 0.0, random.choice(UFS)))
                continue
            w.writerow(linha(lat, lon, random.choice(UFS)))
            if i % 500000 == 0:
                print("  disperso %d" % i, file=sys.stderr)

if __name__ == "__main__":
    main()
