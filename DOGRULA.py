#!/usr/bin/env python3
"""M3 acik malzeme arsivi — okura donuk dogrulama.

NE YAPAR: arsivdeki her kaynagin TAM sha256'sini yeniden hesaplar ve kanonik kayitta
(kanonik/KANONIK.json -> _kaynaklar[*].sha256) yazili ozetle karsilastirir. Tek bir bayt
degisse uyusmazlik bildirilir.

Kayit ayrica geriye donuk uyum icin 12 karaktere kirpilmis md5 de tasir (`md5` alani);
dogrulama TAM sha256 ile yapilir.

IKI AYAKLI DOGRULAMA (22-23.10):
  [1/2] 14 VERI KAYNAGI  <- kanonik/KANONIK.json -> _kaynaklar[*].sha256
  [2/2] ARSIVIN TAMAMI   <- MANIFEST.sha256 (kod dosyalari DAHIL)
Ikinci ayak, Mac-inceleme'nin 23.10 bulgusuyla eklendi: birinci ayak yalniz veri
kaynaklarini kapsiyordu, dolayisiyla bir okur URET_kanonik.py ya da mde.py'yi degistirip
yeniden kossa farkli sayilar alir ve dogrulama yine "14/14 gecti" derdi.
KAPSAM DISI: MANIFEST.sha256 kendi ozetini icermez.

NE YAPMAZ: kanonik/URET_kanonik.py --dogrula kapisini kosmaz. O kapi, kaydin KAYNAK
DEPOYA islenen bayt dizisinden (git show HEAD:) dogrulanmasini sinar ve dolayisiyla
YALNIZ kaynak deposunda anlamlidir; bu arsiv bir git deposu degil. Arsivde anlamli olan
dogrulama, dosyalarin ozetleri ile kayittaki ozetlerin ayni olmasidir -- bu betigin
yaptigi tam olarak budur.

Kullanim:  python3 DOGRULA.py
Cikis   :  0 = tum ozetler uyusuyor · 1 = en az bir uyusmazlik
"""
import hashlib, json, os, sys

KOK = os.path.dirname(os.path.abspath(__file__))

def sha256(yol):
    """Kanonik kayit TAM sha256 tasiyor (22.10'dan beri); dogrulama onunla yapilir."""
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()

def main():
    kayit = os.path.join(KOK, "kanonik", "KANONIK.json")
    if not os.path.exists(kayit):
        print("HATA: kanonik/KANONIK.json bulunamadi"); return 1
    K = json.load(open(kayit, encoding="utf-8"))
    ks = K.get("_kaynaklar", {})
    tam, uyusan, eksik, uyusmayan = 0, 0, [], []
    print(f"M3 acik malzeme — {len(ks)} kaynak dogrulaniyor\n")
    for ad, v in sorted(ks.items()):
        if not isinstance(v, dict) or not v.get("yol"):
            continue
        tam += 1
        yol = os.path.join(KOK, v["yol"])
        beklenen = v.get("sha256")
        if not os.path.exists(yol):
            eksik.append((ad, v["yol"])); print(f"  EKSIK      {ad:20} {v['yol']}"); continue
        if not beklenen:
            print(f"  OZET YOK   {ad:20} {v['yol']}"); continue
        gercek = sha256(yol)
        if gercek == beklenen:
            uyusan += 1
            print(f"  TAMAM      {ad:20} {beklenen[:16]}…")
        else:
            uyusmayan.append((ad, beklenen, gercek))
            print(f"  UYUSMAZ    {ad:20} beklenen {beklenen[:16]}… · bulunan {gercek[:16]}…")
    print(f"\n  [1/2] kaynaklar: {uyusan}/{tam} ozet uyusuyor")
    if eksik:     print(f"  eksik dosya : {len(eksik)}")
    if uyusmayan: print(f"  UYUSMAYAN   : {len(uyusmayan)}")
    kaynak_ok = (uyusan == tam and not eksik and not uyusmayan)

    # ---- [2/2] TUM ARSIV, MANIFEST.sha256'ya karsi ----
    print("\n  [2/2] tum arsiv (MANIFEST.sha256):")
    mf = os.path.join(KOK, "MANIFEST.sha256")
    if not os.path.exists(mf):
        print("    MANIFEST.sha256 YOK -- arsiv eksik"); return 1
    beklenenler = {}
    for satir in open(mf, encoding="utf-8"):
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        h, _, rel = satir.partition("  ")
        beklenenler[rel] = h
    ATLA = {"MANIFEST.sha256"}   # TEK uye; beyan ile birebir (bkz. KAPSAM DISI satiri)
    mevcut = set()
    for kok, dizinler, adlar in os.walk(KOK):
        dizinler[:] = [d for d in dizinler if d not in (".git", "__pycache__")]
        for ad in adlar:
            rel = os.path.relpath(os.path.join(kok, ad), KOK)
            if rel in ATLA or rel.endswith(".pyc"):
                continue
            mevcut.add(rel)
    m_uyusan, m_uyusmayan, m_eksik, m_fazla = 0, [], [], sorted(mevcut - set(beklenenler))
    for rel, beklenen in sorted(beklenenler.items()):
        yol = os.path.join(KOK, rel)
        if not os.path.exists(yol):
            m_eksik.append(rel); print(f"    EKSIK      {rel}"); continue
        g = sha256(yol)
        if g == beklenen:
            m_uyusan += 1
        else:
            m_uyusmayan.append(rel)
            print(f"    UYUSMAZ    {rel}")
            print(f"               beklenen {beklenen[:16]}… · bulunan {g[:16]}…")
    for rel in m_fazla:
        print(f"    MANIFESTODA YOK  {rel}")
    print(f"    {m_uyusan}/{len(beklenenler)} dosya uyusuyor"
          f"{f' · uyusmayan {len(m_uyusmayan)}' if m_uyusmayan else ''}"
          f"{f' · eksik {len(m_eksik)}' if m_eksik else ''}"
          f"{f' · manifestoda yok {len(m_fazla)}' if m_fazla else ''}")
    arsiv_ok = (m_uyusan == len(beklenenler) and not m_uyusmayan and not m_eksik and not m_fazla)

    print("\n  KAPSAM DISI (beyan): MANIFEST.sha256 kendi ozetini icermez;"
          " bu dosyanin butunlugu arsiv icinden dogrulanamaz.")
    if kaynak_ok and arsiv_ok:
        print("\n  DOGRULAMA GECTI: 14 kaynak kanonik kayitla, arsivin tamami manifestoyla ayni.")
        return 0
    print("\n  DOGRULAMA GECMEDI.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
