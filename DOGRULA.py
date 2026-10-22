#!/usr/bin/env python3
"""M3 acik malzeme arsivi — okura donuk dogrulama.

NE YAPAR: arsivdeki her kaynagin TAM sha256'sini yeniden hesaplar ve kanonik kayitta
(kanonik/KANONIK.json -> _kaynaklar[*].sha256) yazili ozetle karsilastirir. Tek bir bayt
degisse uyusmazlik bildirilir.

Kayit ayrica geriye donuk uyum icin 12 karaktere kirpilmis md5 de tasir (`md5` alani);
dogrulama TAM sha256 ile yapilir.

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
    print(f"\n  sonuc: {uyusan}/{tam} ozet uyusuyor")
    if eksik:     print(f"  eksik dosya : {len(eksik)}")
    if uyusmayan: print(f"  UYUSMAYAN   : {len(uyusmayan)}")
    if uyusan == tam and not eksik and not uyusmayan:
        print("\n  DOGRULAMA GECTI: arsivdeki her kaynak, kanonik kayittaki ozetiyle ayni.")
        return 0
    print("\n  DOGRULAMA GECMEDI.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
