"""M3 icin MDE tablosu. scipy yok -> t dagilimi elle, BILINEN DEGERLERE ankrajlanarak."""
import math


def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN: d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN: c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS: break
    return h


def betai(a, b, x):
    """duzenlenmis eksik beta I_x(a,b)"""
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    p = 0.5 * betai(df / 2.0, 0.5, x)
    return 1.0 - p if t > 0 else p


def t_ppf(p, df):
    lo, hi = -400.0, 400.0
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p: lo = mid
        else: hi = mid
    return (lo + hi) / 2.0


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------- OZ-SINAMA (ankraj) ----------------
print("=== OZ-SINAMA: bilinen t degerleri (tutmazsa asagisi gecersiz) ===")
cases = [(0.975, 29, 2.045, "makalenin kendi kullandigi t_29 (satir 146)"),
         (0.975, 1, 12.706, "t_{0,975;1}"),
         (0.975, 10, 2.228, "t_{0,975;10}"),
         (0.80, 10, 0.879, "t_{0,80;10}"),
         (0.975, 1000, 1.962, "t_{0,975;1000} ~ z")]
ok = True
for p, df, bek, ad in cases:
    g = t_ppf(p, df)
    tut = abs(g - bek) < 0.002
    ok &= tut
    print("  %-42s beklenen %8.3f  hesap %8.4f  %s" % (ad, bek, g, "TUTTU" if tut else "TUTMADI"))
print("  -> %s\n" % ("ANKRAJ TUTTU, asagisi gecerli" if ok else "ANKRAJ TUTMADI - KULLANMA"))
if not ok:
    raise SystemExit(1)


def mde_ind(n):
    df = 2 * n - 2
    return (t_ppf(0.975, df) + t_ppf(0.80, df)) * math.sqrt(2.0 / n)


def mde_paired(n):
    df = n - 1
    return (t_ppf(0.975, df) + t_ppf(0.80, df)) / math.sqrt(n)


print("=== MDE (sigma birimi) · guc %80 · alfa 0,05 iki yanli ===")
print("%5s | %-24s | %-24s" % ("n", "BAGIMSIZ (df=2n-2)", "ESLESMIS (df=n-1)"))
print("-" * 58)
for n in [1, 2, 3, 5, 10, 30]:
    if n == 1:
        print("%5d | %-24s | %-24s" % (n, "TANIMSIZ (df=0)", "TANIMSIZ (df=0)"))
    else:
        print("%5d | %-24s | %-24s" % (n, "%.3f sigma" % mde_ind(n), "%.3f sigma_fark" % mde_paired(n)))

print("\n=== M3'UN KENDI FARKLARI: saptamak icin gereken n (bagimsiz, KOL BASINA) ===")
for d, ad in [(0.6, "en yakin uc aile (v9/v8/v5): 0,6 puan"),
              (9.0, "v9 - v10: ~9 puan"),
              (1.24, "alti kollu kiyastaki 1,24 puan"),
              (2.1, "iki bagimsiz egitim medyan farki 2,1 puan")]:
    satir = "  %-40s" % ad
    for sd in [4.38, 5.0]:
        n = 2
        while n <= 20000 and mde_ind(n) * sd > d:
            n += 1
        satir += "  sigma=%.2f -> n=%s" % (sd, n if n <= 20000 else ">20000")
    print(satir)

print("\n=== TEK KOSUMLA DOGRU SIRALAMA OLASILIGI  P = Phi(delta/(sigma*sqrt2)) ===")
for d, ad in [(0.6, "0,6 puan"), (1.24, "1,24 puan"), (2.1, "2,1 puan"), (9.0, "9 puan")]:
    print("  %-12s sigma=4,38 -> P = %.4f   sigma=5,00 -> P = %.4f"
          % (ad, norm_cdf(d / (4.38 * math.sqrt(2))), norm_cdf(d / (5.0 * math.sqrt(2)))))
