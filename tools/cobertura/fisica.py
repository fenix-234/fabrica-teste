import math

def horizon_km(ht, hr, k=4/3):
    # raio efetivo da Terra k*R; d = sqrt(2*k*R*h)
    R = 6371000.0
    return (math.sqrt(2*k*R*ht) + math.sqrt(2*k*R*hr))/1000.0

def eirp_re_dbm(eirp_total_dbm, n_rb):
    return eirp_total_dbm - 10*math.log10(12*n_rb)

def budget_db(eirp_re, rsrp_target, corpo_agua, margem_sombra):
    return eirp_re - rsrp_target - corpo_agua - margem_sombra

def d_freespace_km(budget, f_mhz):
    # FSPL = 32.44 + 20log10(f_MHz) + 20log10(d_km)
    return 10**((budget - 32.44 - 20*math.log10(f_mhz))/20)

def d_tworay_km(budget, ht, hr):
    # PL = 40log10(d_m) - 20log10(ht) - 20log10(hr)
    x = (budget + 20*math.log10(ht) + 20*math.log10(hr))/40
    return (10**x)/1000.0

def breakpoint_km(ht, hr, f_mhz):
    lam = 299.792458/f_mhz
    return (4*ht*hr/lam)/1000.0

EIRP=60.0; NRB=100; RSRP=-110.0; CORPO=10.0; SOMBRA=8.0
ere = eirp_re_dbm(EIRP, NRB)
B = budget_db(ere, RSRP, CORPO, SOMBRA)
print("Premissas: EIRP total %.0f dBm | 20 MHz (100 RB) | RSRP alvo %.0f dBm" % (EIRP,RSRP))
print("           perda corpo+imersao %.0f dB | margem de sombreamento %.0f dB" % (CORPO,SOMBRA))
print("EIRP por resource element = %.1f dBm  ->  orcamento de perda = %.1f dB\n" % (ere,B))

print("=== A. HORIZONTE DE RADIO (k=4/3) — teto geometrico absoluto, em km ===")
alturas_user=[("nadando/derivando",0.3),("deitado na prancha",0.8),("de pe na prancha",1.5),("jetski/barco",3.0)]
torres=[20,30,45,60,100]
print("%-22s %s" % ("usuario", "".join("torre %3dm " % t for t in torres)))
for nome,hr in alturas_user:
    print("%-22s %s" % (nome, "".join("%9.1f " % horizon_km(t,hr) for t in torres)))

print("\n=== B. ALCANCE POR ORCAMENTO DE ENLACE, usuario a 0.8 m (deitado na prancha) ===")
print("%-9s %10s %10s %10s %10s" % ("freq","breakpt","2-raios","esp.livre","horizonte"))
for f in [700,850,1800,2100,2600,3500]:
    ht=30; hr=0.8
    print("%-9s %9.2f %9.1f %9.1f %9.1f" % (str(f)+" MHz", breakpoint_km(ht,hr,f), d_tworay_km(B,ht,hr), d_freespace_km(B,f), horizon_km(ht,hr)))

print("\n=== C. FAIXA PRATICA por altura de torre (700 MHz, usuario 0.8 m) ===")
print("%-12s %10s %10s %10s %10s" % ("torre","2-raios","esp.livre","horizonte","faixa util"))
for ht in torres:
    hr=0.8
    tr=d_tworay_km(B,ht,hr); fs=d_freespace_km(B,700); hz=horizon_km(ht,hr)
    teto=min(fs,hz)
    print("%-12s %9.1f %9.1f %9.1f   %.1f a %.1f km" % (str(ht)+" m", tr, fs, hz, tr, teto))

print("\n=== D. EFEITO DA PERDA POR CORPO/IMERSAO (700 MHz, torre 30 m, usuario 0.8 m) ===")
for corpo in [0,5,10,15,20]:
    b = budget_db(ere,RSRP,corpo,SOMBRA)
    print("  perda %2d dB -> 2-raios %5.1f km | espaco livre %5.1f km" % (corpo, d_tworay_km(b,30,0.8), d_freespace_km(b,700)))

print("\n=== E. PRIMEIRA ZONA DE FRESNEL no ponto medio (raio em metros) ===")
print("%-10s %s" % ("distancia", "".join("%8d MHz" % f for f in [700,1800,2600])))
for d in [1,2,5,10,20]:
    row=""
    for f in [700,1800,2600]:
        r = 17.31*math.sqrt((d/2)*(d/2)/((f/1000.0)*d))
        row += "%12.1f" % r
    print("%-10s %s" % (str(d)+" km", row))
