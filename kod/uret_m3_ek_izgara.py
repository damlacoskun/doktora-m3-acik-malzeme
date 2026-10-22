"""M3 ek malzemesi: 43 varyantlik tam izgara tablosunu KANONIK CSV'den uretir.
Proje kurali (hafiza: grafik/tablo kanonik okuma): deger elle gomulmez, kanonik
kayittan okunur ve oge sayisi dogrulanir."""
import csv, os, sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(_KOK, "kanonik", "_910_EK6_504_sinif_bazli_20260910.csv")
CIKTI = os.path.join(_KOK, "Makale3_EK_izgara504.tex")

AILE_SIRA = {"3": 0, "4": 1, "5": 2, "6": 3, "7": 4, "8": 5, "9": 6, "10": 7, "11": 8, "12": 9}
OLCEK_SIRA = {"n": 0, "tiny": 0, "s": 1, "m": 2, "l": 3, "c": 4, "x": 5, "w6": 6, "e6": 7, "d6": 8, "e6e": 9}


def anahtar(ad):
    g = ad.replace("YOLOv", "").replace("YOLO", "")
    if "-" in g:
        aile, olcek = g.split("-", 1)
    else:
        aile, olcek = g, ""
    return (AILE_SIRA.get(aile, 99), OLCEK_SIRA.get(olcek, 50), ad)


def say(x, b=3):
    if x in (None, "", "nan"):
        return "---"
    return f"{float(x):.{b}f}".replace(".", "{,}")


def main():
    R = list(csv.DictReader(open(KAYNAK, encoding="utf-8")))
    assert len(R) == 504, f"kanonik dosya 504 satir olmali, {len(R)} bulundu"
    modeller = sorted({r["ek6_ad"] for r in R}, key=anahtar)
    assert len(modeller) == 43, f"43 model olmali, {len(modeller)} bulundu"
    hucre = {}
    for r in R:
        hucre.setdefault(r["ek6_ad"], []).append(r)
    eksik = {m: len(v) for m, v in hucre.items() if len(v) != 12}
    toplam = sum(len(v) for v in hucre.values())
    assert toplam == 504, toplam

    L = []
    L.append(r"% OTOMATIK URETILDI: kod/uret_m3_ek_izgara.py · kaynak kanonik/_910_EK6_504_sinif_bazli_20260910.csv")
    L.append(r"% Elle duzenlemeyin; kaynak degisirse betigi yeniden kosun.")
    L.append(r"\footnotesize")
    L.append(r"\begin{longtable}{llrrrrr}")
    L.append(r"\caption{Ek malzeme: 43 model--\"ol\c{c}ek varyant\i n\i n tam de\u{g}erlendirme \i zgaras\i\ "
             r"(504 h\"ucre). De\u{g}erlendirme h\"ucresi conf $0{,}001$ / IoU $0{,}5$; "
             r"t\"um de\u{g}erler INbreast test b\"ol\"unmesinde \"ol\c{c}\"ulm\"u\c{s}t\"ur. "
             r"D\"ort y\"uksek-\c{c}\"oz\"un\"url\"uk YOLOv7 varyant\i\ (d6, e6, e6e, w6) "
             r"$608$ piksel giri\c{s}te ko\c{s}ulmad\i\u{g}\i\ i\c{c}in 12 yerine 9 h\"ucre ta\c{s}\i r; "
             r"bu eksiklik gizlenmemi\c{s}, h\"ucre say\i s\i\ ile birlikte verilmi\c{s}tir. S\"utunlar: px giri\c{s} \c{c}\"oz\"un\"url\"u\u{g}\"u, mAP$_{50}$ genel mAP@0,5, mAP$_{50:95}$ genel mAP@0,5:0,95, mAP$_{50}^{\mathrm{mal}}$ malign s\i n\i f mAP@0,5, mAP$_{50}^{\mathrm{mal}}$ malign s\i n\i f mAP@0,5. $F_1$ bu tabloda VERILMEMEKTEDIR: ana metin $F_1$ de\u{g}erlerini klinik \c{c}al\i \c{s}ma noktas\i nda (conf $0{,}25$) raporlar, bu tablo ise mAP h\"ucresinden (conf $0{,}001$) \"uretilmi\c{s}tir; iki \"ol\c{c}\"ut\"u ayn\i\ tabloda vermek g\"ovde ile ek aras\i nda uyu\c{s}mazl\i k yarat\i rd\i .}\\")
    L.append(r"\label{tab:ek-izgara504} \\")
    L.append(r"\toprule")
    bas = (r"\textbf{Model} & \textbf{Aile} & \textbf{px} & \textbf{Epok} & "
           r"\textbf{mAP$_{50}$} & \textbf{mAP$_{50:95}$} & \textbf{mAP$_{50}^{\mathrm{mal}}$} \\")
    L.append(bas)
    L.append(r"\midrule")
    L.append(r"\endfirsthead")
    L.append(r"\toprule")
    L.append(bas)
    L.append(r"\midrule")
    L.append(r"\endhead")
    L.append(r"\bottomrule")
    L.append(r"\endfoot")
    L.append("")
    n = 0
    for m in modeller:
        for r in sorted(hucre[m], key=lambda x: (int(x["ImageSize"]), int(x["epoch"]))):
            L.append(f"{m} & {r['aile']} & {r['ImageSize']} & {r['epoch']} & "
                     f"{say(r['mAP50_all'])} & {say(r['mAP5095_all'])} & "
                     f"{say(r['mAP50_malign'])} \\\\")
            n += 1
    L.append(r"\end{longtable}")
    assert n == 504, f"yazilan satir {n} != 504"
    open(CIKTI, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"yazildi: {CIKTI}")
    print(f"  model {len(modeller)} · satir {n} · 12 hucresi olmayan {eksik}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
