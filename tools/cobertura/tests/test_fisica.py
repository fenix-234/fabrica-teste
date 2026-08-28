#!/usr/bin/env python3
"""Testes do motor de alcance e do leitor. Sem dependencias: python3 tests/test_fisica.py"""
import importlib.util, math, os, sys, tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ec", os.path.join(BASE, "estimar_cobertura.py"))
ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)

falhas = []
def perto(nome, obtido, esperado, tol):
    ok = abs(obtido - esperado) <= tol
    print("%-52s %10.3f  (esperado %.3f ± %.3f)  %s"
          % (nome, obtido, esperado, tol, "ok" if ok else "FALHOU"))
    if not ok: falhas.append(nome)

def igual(nome, obtido, esperado):
    ok = obtido == esperado
    print("%-52s %-22r %s" % (nome, obtido, "ok" if ok else "FALHOU (esperado %r)" % (esperado,)))
    if not ok: falhas.append(nome)

CFG = {"h_usuario":0.8,"eirp_padrao":60.0,"n_rb":100,"rsrp":-110.0,"perda_corpo":10.0,
       "margem":8.0,"fator_calibracao":1.5,"raio_busca":60.0,"altura_padrao":30.0,
       "freq_padrao":850.0,"usar_azimute":True}

print("\n--- horizonte de radio (k=4/3) ---")
perto("torre 30 m, usuario 0,8 m", ec.horizonte_km(30, 0.8), 26.3, 0.1)
perto("torre 30 m, usuario 0,3 m", ec.horizonte_km(30, 0.3), 24.8, 0.1)
perto("torre 100 m, usuario 3 m",  ec.horizonte_km(100, 3.0), 48.4, 0.1)

print("\n--- orcamento de enlace ---")
orc = ec.eirp_por_re(60.0, 100) - (-110.0) - 10.0 - 8.0
perto("EIRP por resource element (60 dBm, 20 MHz)", ec.eirp_por_re(60.0, 100), 29.2, 0.1)
perto("orcamento total", orc, 121.2, 0.1)

print("\n--- alcance ---")
perto("dois raios, torre 30 m, usuario 0,8 m", ec.alcance_dois_raios_km(orc, 30, 0.8), 5.3, 0.1)
perto("dois raios, torre 100 m",               ec.alcance_dois_raios_km(orc, 100, 0.8), 9.6, 0.1)
perto("espaco livre 700 MHz",                  ec.alcance_espaco_livre_km(orc, 700), 39.2, 0.2)
perto("espaco livre 3500 MHz",                 ec.alcance_espaco_livre_km(orc, 3500), 7.8, 0.1)
perto("breakpoint 700 MHz (km)",               ec.breakpoint_km(30, 0.8, 700), 0.224, 0.005)

print("\n--- invariantes fisicas ---")
d1 = ec.alcance_dois_raios_km(orc, 30, 0.8)
d2 = ec.alcance_dois_raios_km(orc, 60, 0.8)
perto("dobrar a torre multiplica o alcance por 1,41", d2/d1, math.sqrt(2), 0.01)
f1 = ec.alcance_espaco_livre_km(orc, 700)
f2 = ec.alcance_espaco_livre_km(orc, 1400)
perto("dobrar a frequencia corta o espaco livre pela metade", f1/f2, 2.0, 0.01)
a = ec.alcance_dois_raios_km(orc, 30, 0.8)
b = ec.alcance_dois_raios_km(orc - 12, 30, 0.8)
perto("12 dB a menos corta o alcance de dois raios pela metade", a/b, 2.0, 0.01)

print("\n--- atenuacao de setor ---")
igual("alvo no lobo principal (0 grau)",   ec.atenuacao_setor_db(90, 90, CFG), 0.0)
igual("alvo a 59 graus",                   ec.atenuacao_setor_db(90, 149, CFG), 0.0)
igual("alvo a 90 graus (lateral)",         ec.atenuacao_setor_db(90, 180, CFG), 12.0)
igual("alvo a 180 graus (costas)",         ec.atenuacao_setor_db(90, 270, CFG), 20.0)
igual("cruzando 360 graus",                ec.atenuacao_setor_db(350, 10, CFG), 0.0)
igual("sem azimute informado",             ec.atenuacao_setor_db(None, 10, CFG), 0.0)
igual("azimute desligado por opcao",       ec.atenuacao_setor_db(90, 270, {**CFG, "usar_azimute": False}), 0.0)

print("\n--- geometria ---")
perto("haversine Fortaleza-Natal", ec.haversine_km(-3.7392,-38.4611,-5.7945,-35.2110), 435.0, 15.0)
la, lo = ec.destino_km(-3.0, -40.0, 90.0, 10.0)
perto("destino 10 km a leste: distancia de volta", ec.haversine_km(-3.0,-40.0,la,lo), 10.0, 0.01)
perto("destino 10 km a leste: azimute de volta",   ec.azimute_entre(-3.0,-40.0,la,lo), 90.0, 0.1)
perto("azimute para o norte", ec.azimute_entre(-3.0,-40.0,-2.0,-40.0), 0.0, 0.1)
perto("azimute para o sul",   ec.azimute_entre(-3.0,-40.0,-4.0,-40.0), 180.0, 0.1)

print("\n--- leitura de coordenadas ---")
perto("decimal com ponto",   ec._coord("-3.7392"), -3.7392, 1e-9)
perto("decimal com virgula", ec._coord("-3,7392"), -3.7392, 1e-9)
perto("grau-minuto-segundo", ec._coord("-3 44 21.1"), -3.73919, 1e-4)
igual("vazio",  ec._coord(""), None)
igual("lixo",   ec._coord("N/D"), None)

print("\n--- cabecalho com BOM ---")
igual("BOM utf-8 decodificado",      ec._norm("﻿NomeEntidade"), "nomeentidade")
igual("BOM lido como latin-1",       ec._norm("ï»¿NomeEntidade"), "nomeentidade")
igual("acento e espaco no cabecalho", ec._norm("Altura Antena"), "alturaantena")

print("\n--- classificacao ---")
igual("sem estacao",      ec.classificar(0, 0), "SEM COBERTURA")
igual("1,5 km",           ec.classificar(1.5, 3), "CRITICO")
igual("4 km",             ec.classificar(4.0, 3), "LIMITADO")
igual("8 km",             ec.classificar(8.0, 3), "ACEITAVEL")
igual("15 km",            ec.classificar(15.0, 3), "BOM")

print("\n--- filtro de celulas ---")
cells = ec.celulas_uteis([{"lat":"-3.0","lon":"-40.0"}], 60.0)
igual("celula do proprio spot esta no conjunto", ec._celula(-3.0,-40.0) in cells, True)
igual("celula a 50 km esta no conjunto",         ec._celula(-3.45,-40.0) in cells, True)
igual("celula a 300 km esta fora",               ec._celula(-6.0,-40.0) in cells, False)

print("\n--- leitura ponta a ponta ---")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "erb.csv")
    with open(p, "w", encoding="latin-1", newline="") as fh:
        fh.write("ï»¿NomeEntidade;Latitude;Longitude;AlturaAntena;FreqTxMHz;"
                 "GanhoAntena;PotenciaTransmissorWatts;AzimuteAntena;UF\n")
        fh.write("CLARO S.A.;-3,0100;-40,0100;45,0;700;16,0;40,00;180;CE\n")
        fh.write("TIM S A;0,0;0,0;30;850;15;20;0;CE\n")            # sujeira
        fh.write("VIVO;nao informado;-40,0;30;850;15;20;90;CE\n")   # sujeira
    erbs = ec.ler_erbs(p, CFG, ec.celulas_uteis([{"lat":"-3.0","lon":"-40.0"}], 60.0), None, None)
    igual("linhas sujas descartadas", len(erbs), 1)
    igual("operadora lida apesar do BOM", erbs[0].operadora, "CLARO S.A.")
    perto("EIRP calculado da potencia e do ganho", erbs[0].eirp, 10*math.log10(40*1000)+16.0, 0.01)
    perto("altura com virgula decimal", erbs[0].altura, 45.0, 1e-9)

print()
if falhas:
    print("FALHAS: %d -> %s" % (len(falhas), ", ".join(falhas)))
    sys.exit(1)
print("todos os testes passaram")
