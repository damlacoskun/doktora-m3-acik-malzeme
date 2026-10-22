import csv, io, os, collections

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "veri", "_504_cozulen_optimizer_155_20261013.csv")
CIKTI = os.path.join(KOK, "taslaklar", "Makale3_EK_optimizer.tex")

def tr(x):
    return str(x).replace(".", "{,}")

with io.open(KAYNAK, newline="", encoding="utf-8") as f:
    R = list(csv.DictReader(f))

def kod(x):
    ist = (x.get("optimizer_istenen") or "").strip()
    coz = (x.get("optimizer_cozulen") or "").strip()
    dv = (x.get("dizin_var") or "").strip()
    if not ist:
        neden = "koşum dizini yok" if dv == "False" else "kayıt alanı korunmamış"
        return "---", "---" if coz == "COZULEMEDI" else coz, neden
    if coz == "COZULEMEDI":
        return ist, "---", ("koşum dizini yok" if dv == "False" else "ilk epok öğrenme oranı okunamadı")
    return ist, coz, ""

sayim = collections.Counter()
sat = []
for x in sorted(R, key=lambda z: (z.get("ek6_ad",""), int(z.get("ImageSize") or 0), int(z.get("epoch") or 0))):
    ist, coz, neden = kod(x)
    sayim[(ist, coz)] += 1
    lr = (x.get("ilk_epok_lr") or "").strip()
    nb = (x.get("nb") or "").strip()
    try: nb = str(int(float(nb)))
    except Exception: pass
    sat.append("%s & %s & %s & %s & %s & %s & %s & %s \\\\" % (
        x.get("ek6_ad","").replace("_","\\_"), x.get("ImageSize",""), x.get("epoch",""),
        ist if ist != "---" else "---", coz if coz != "---" else "---",
        tr(lr) if lr else "---", nb if nb else "---", neden))

ist_d = collections.Counter((z.get("optimizer_istenen") or "").strip() or "kayıtsız" for z in R)
coz_d = collections.Counter((z.get("optimizer_cozulen") or "").strip() for z in R)
dz = sum(1 for z in R if (z.get("dizin_var") or "").strip() == "False")

L = []
L.append("% OTOMATIK URETILDI: kod/uret_m3_ek_optimizer.py · kaynak veri/_504_cozulen_optimizer_155_20261013.csv")
L.append("% Elle duzenlemeyin; kaynak degisirse betigi yeniden kosun.")
L.append("\\footnotesize")
L.append("\\begin{longtable}{lrrlllll}")
L.append("\\caption{Ek malzeme: \\textbf{istenen ve çözülmüş optimizasyon yöntemi dökümü} "
         "(ızgaranın $%d$ hücresi). \\emph{İstenen} sütunu koşumun yapılandırma kaydında ne yazdığını, "
         "\\emph{çözülmüş} sütunu çatının fiilen ne kullandığını verir; ikisinin ayrışabilmesi bu çalışmanın "
         "bildirdiği tekrarlanabilirlik kusurudur. Çözülmüş değer iki bağımsız yoldan geri kazanılmıştır: "
         "ilk epokta kaydedilen öğrenme oranından ($lr$ sütunu; ısınma uzunluğu epok başına toplu iş sayısına "
         "bağlı olduğundan bu değer çözülmüş toplu iş boyutunu da verir, $n_b$ sütunu) ve kontrol noktalarının "
         "taşıdığı çözülmüş alandan. \\textbf{Kapsam eksiksiz değildir ve gizlenmemiştir:} istenen değer "
         "$%d$ hücrede kayıtlıdır ($%d$'ünde \\texttt{SGD}, $%d$'ünde \\texttt{auto}), $%d$ hücrede kayıt "
         "korunmamıştır; çözülmüş değer $%d$ hücrede geri kazanılmış, $%d$ hücrede kazanılamamıştır ve "
         "bunların $%d$'inde koşum dizini artık mevcut değildir. Son sütun her boş hücrenin nedenini "
         "vermektedir. \\texttt{auto} yazan hücrelerin tamamı altı bin epokluktur.}\\\\"
         % (len(R), sum(v for k,v in ist_d.items() if k!="kayıtsız"), ist_d.get("SGD",0),
            ist_d.get("auto",0), ist_d.get("kayıtsız",0), coz_d.get("SGD",0),
            coz_d.get("COZULEMEDI",0), dz))
L.append("\\label{tab:ek-optimizer} \\\\")
BAS = ("\\textbf{Hücre} & \\textbf{px} & \\textbf{Epok} & \\textbf{İstenen} & \\textbf{Çözülmüş} & "
       "\\textbf{ilk epok $lr$} & \\textbf{$n_b$} & \\textbf{boşluğun nedeni} \\\\")
L += ["\\toprule", BAS, "\\midrule", "\\endfirsthead", "\\toprule", BAS, "\\midrule", "\\endhead",
      "\\bottomrule", "\\endfoot", ""]
L += sat
L.append("\\end{longtable}")

io.open(CIKTI, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("uretildi: %s · %d satir · istenen %s · cozulen %s · dizinsiz %d"
      % (CIKTI, len(sat), dict(ist_d), dict(coz_d), dz))
