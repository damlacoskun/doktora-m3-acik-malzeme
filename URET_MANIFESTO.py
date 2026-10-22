#!/usr/bin/env python3
"""MANIFEST.sha256 URETIR -- arsivdeki HER dosyanin tam sha256'si.

MIMARI KURAL: manifesto bir CIKTIDIR, elle duzenlenmez. Dogrulayici (DOGRULA.py) onu
yalniz OKUR, asla yazmaz -- kendi referansini yeniden yazabilen bir dogrulayici,
dogrulayici degildir.

TEK ISTISNA BEYAN EDILIR: MANIFEST.sha256 kendi ozetini icermez (icerse ozet kendini
degistirir). Arsivin geri kalaninin tamami kapsanir, KANONIK.json dahil.
"""
import hashlib, os, sys

KOK = os.path.dirname(os.path.abspath(__file__))
MANIFESTO = "MANIFEST.sha256"
# TEK uyeli dislama: yalniz manifestonun kendisi. .gitignore ozetlenebilir ve
# ozyinelemeli degil -> manifestoya GIRER (bagimsiz denetim 23.10: kodun dislama
# kumesi iki uyeliyken beyan bir uyeliydi).
ATLA = {MANIFESTO}

def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()

def dosyalar():
    for kok, dizinler, adlar in os.walk(KOK):
        dizinler[:] = [d for d in dizinler if d not in (".git", "__pycache__")]
        for ad in sorted(adlar):
            rel = os.path.relpath(os.path.join(kok, ad), KOK)
            if rel in ATLA or rel.endswith(".pyc"):
                continue
            yield rel

def main():
    satirlar = [f"{sha256(os.path.join(KOK, r))}  {r}" for r in sorted(dosyalar())]
    with open(os.path.join(KOK, MANIFESTO), "w", encoding="utf-8") as f:
        f.write("# M3 acik malzeme arsivi -- tam sha256 manifestosu\n")
        f.write(f"# URET_MANIFESTO.py tarafindan URETILDI; elle duzenlenmez.\n")
        f.write(f"# KAPSAM DISI (beyan): {MANIFESTO} kendi ozetini icermez.\n")
        f.write("\n".join(satirlar) + "\n")
    print(f"uretildi: {MANIFESTO}  ({len(satirlar)} dosya)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
