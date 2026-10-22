#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URET_kanonik.py — KANONIK SAYI KAYDINI VERIDEN URETIR.

NEDEN VAR: 22.08 taslaklarinda n=26 ara degerleri donmus kalmisti; tez ile makaleler
arasinda sessiz sapma olustu. Cozum, sayilari ELLE yazmak degil, tek bir yerden
URETMEK. Deney bittikce bu script yeniden kosulur, kayit kendini gunceller.

CIKTI: KANONIK.md  (insan okur) + KANONIK.json (ajanlar okur)

KURAL: Bir sayi bu kayitta yoksa makalede kullanilamaz.
       Bu kayittaki her sayinin 'kaynak' alani vardir; iddia oraya kadar izlenebilir.
"""
import csv, json, math, os, re, statistics as st, datetime, hashlib, subprocess
import sys as _sys

# DOGRULAMA KIPI (18.10, Mac-inceleme bulgusu): Katman 0'in temel kurali --
# "KANONIK.json elle duzenlenmez, URET_kanonik.py ile uretilir" -- hicbir seyle
# UYGULANMIYORDU; bir BEYANDI. Butun gun beyanlari atesleyen kontrollere cevirdik
# (ileti etiketi kapisi, sozdizimi kancasi, cerceve demiri, izlenebilirlik tarayicisi);
# mimarinin EN ALTINDAKI kural kapisi olmayan tek kuraldi. Ve risk kuramsal degil:
# bugunku bozuk-dosya olayi tam olarak "uretilmis bir yapitin ureticisine elle yama"
# yuzunden cikti. Tuketicilerin hepsi (makale, demirler, es-denetciler) JSON'u okuyor,
# ureticiyi degil -- JSON'a elle yapilmis bir duzeltme GORUNMEZ olur.
#
# Kullanim:  python3 URET_kanonik.py             -> uretir ve yazar
#            python3 URET_kanonik.py --dogrula   -> uretir, YAZMAZ, depodaki ile
#                                                   karsilastirir, fark varsa exit 1
#
# SART (H64): karsilastirma OYNAK alanlari dislar. _uretim bir zaman damgasi; naif bir
# diff her zaman fark bulur, kapi surekli yanlis pozitif verir ve sonunda kapatilir --
# "mesru isi engelleyen bir demir devre disi birakilir". Dislama kapinin calisir halde
# kalmasinin SARTI, susu degil.
_DOGRULA = "--dogrula" in _sys.argv
_OYNAK = ("_uretim",)

# ============================================================================
# MIMARI KURAL (18.10, Mac-inceleme): KAYIT BIR CIKTIDIR, ASLA GIRDI DEGIL.
#
#   Yeni bir sayi hesaplayan her sey HAM CSV'yi okur, kaydi okumaz. Bir blok
#   baska bir blogun degerine ihtiyac duyuyorsa KAYNAKTAN YENIDEN HESAPLAR,
#   kayittan almaz.
#
# Gerekce olculdu: bu betikte 156 round() cagrisi var ve KANONIK.json'daki 3378
# float alanin %94,6'si iki ondalik ya da daha az tutuyor. Bu, kaydin BIRINCIL
# isi icin DOGRU -- makaleye giren sayi iki ondalik olmali ve kaydin ilan edilmis
# gorevi "bir sayi bu kayitta yoksa makalede kullanilamaz". Ama ayni yuvarlama,
# kayit bir HESAP GIRDISI olarak kullanildigi anda hata uretiyor.
#
# Bugun iki kez uretti:
#   3,7538  : makro icin kayittaki yuvarlanmis 0,800953 kullanildi (tam:
#             0,80095324675) -> son hane bozuldu, dogru deger 3,7537
#   0,0     : AP_malign_fark_puan sert sifir gorundu, cunku parti1 degeri alti
#             haneye yuvarlanmisti (gercek fark -1,429e-05)
#
# "Ara sonuclar yuvarlanmaz, yuvarlama yalniz sunum aninda" dersini kayda
# yazdik -- ama KAYIT ZATEN SUNUM ANIDIR; sonraki her hesap icin ara deger olur.
# Dolayisiyla cozum yuvarlamayi kaldirmak degil (o kaydin isini bozar), kaydi
# GIRDI OLARAK KULLANMAMAK.
#
# Denetlendi (18.10): bu betikte K[...][...] 24 satirda kullaniliyor, ARITMETIK
# baglamda 0 satirda. Kural fiilen uyulmus durumda; eksik olan YAZILI OLMAMASIYDI
# -- ve yazili olmadigi icin ikimiz de birer kez kayittan hesapladik.
# ============================================================================

OUT  = os.path.dirname(os.path.abspath(__file__))

# DUZELTME (05.09, 910): BAND yalnizca 155'in yerel yolunda araniyordu. Betik baska bir
# makinede kosuldugunda ark/esli bolumleri SESSIZCE bos uretiliyor, kayit eksik cikiyordu —
# ve o eksik kayit depoya commit'lenip dolu olani eziyordu. Artik depo kopyasi da taranir.
def _ilk_var(*adaylar):
    for a in adaylar:
        if a and os.path.exists(a): return os.path.normpath(a)
    return adaylar[0]

# IZLENEBILIRLIK (17.10): band CSV depo disindaydi -> Kohort A'nin sayilari depodan dogrulanamiyordu.
# Beyan "koşum kayıtlarından türetilmiştir" dedigi icin kaynak depoya alindi; depo-ici kopya birincil,
# depo disi asil yol yalniz yedek olarak denenir (ayni bayt dizisi, CRLF->LF).
_BAND_DEPO = os.path.join(os.path.dirname(OUT), "veri", "_bandA_BIRLESIK_conf0001_20260814.csv")
BAND = _ilk_var(os.environ.get("BAND_CSV"),
                _BAND_DEPO,
                os.path.join(OUT, "BIRLESIK_band_conf0001.csv"),
                "/home/dnnlab7/Desktop/_BAND_REJIM_2FAZ_20260814/BIRLESIK_band_conf0001.csv")
MAP1 = _ilk_var(os.environ.get("MAP1_CSV"),
                os.path.join(OUT, "map1_MEVCUT_ARKLAR.csv"),
                "/home/dnnlab7/Desktop/_BAND_REJIM_2FAZ_20260814/map1_MEVCUT_ARKLAR.csv")

K = {"_uretim": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "_kaynaklar": {}}

def io_open(p):
    return open(p, encoding="utf-8").read()

def sha(p):
    """ADI YANILTICI AMA DEGISTIRILMEDI: md5, 12 karaktere kirpilmis. 14 cagri yeri var ve
    kayitta `md5` alani olarak duruyor; yeniden adlandirmak kaydi degistirirdi.
    Tam sha256 ayri alan olarak _kaynaklar zenginlestirme dongusunde eklenir (bkz. _sha256)."""
    try: return hashlib.md5(open(p,'rb').read()).hexdigest()[:12]
    except: return None

def _sha256(p):
    """Acik malzeme arsivi icin TAM sha256. Kirpilmis md5 (48 bit) kazara bozulmayi yakalar
    ama kasitli kurcalamaya zayif; arsiv kamuya acilacagi icin tam sha256 de kaydedilir
    (kullanici karari 22.10.2026)."""
    try:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for blok in iter(lambda: f.read(1 << 20), b''):
                h.update(blok)
        return h.hexdigest()
    except Exception:
        return None

# DUZELTME (04.09, bes ajanin bagimsiz dogruladigi bulgu): guven araliklari z=1,96 ile
# kuruluyordu. Kucuk orneklemde (n=30) dogru carpan Student t(n-1)'dir; z kullanmak
# araligi DAR gosterir (n=30 icin %4,3). Tez metni dogruydu, kaba olan bu ara kayitti.
_T_YEDEK = {4:2.7764,5:2.5706,6:2.4469,7:2.3646,8:2.3060,9:2.2622,10:2.2281,
            14:2.1448,19:2.0930,24:2.0639,29:2.0452,49:2.0096,99:1.9842}

def t_kritik(n, alfa=0.05):
    """Iki yonlu %95 icin t(n-1) carpani. scipy yoksa tabloya, o da yoksa z'ye duser."""
    df = n - 1
    if df < 1: return float("nan")
    try:
        from scipy import stats
        return float(stats.t.ppf(1 - alfa/2, df))
    except Exception:
        K["_uyarilar"] = K.get("_uyarilar", [])
        if "scipy yok - t carpani tablodan/yaklasik alindi" not in K["_uyarilar"]:
            K["_uyarilar"].append("scipy yok - t carpani tablodan/yaklasik alindi")
        if df in _T_YEDEK: return _T_YEDEK[df]
        yakin = min(_T_YEDEK, key=lambda d: abs(d - df))
        return _T_YEDEK[yakin] if df < 100 else 1.96

# TASARIM KARARI (27.08, kanit-denetci bulgusu): kohort seed 0-29'dur.
# map1/taban kolunda 31. bir kosum var (seed 30, makine 910) — 30-tohumlu bandin
# PARCASI DEGIL. Tez her yerde "30-tohumlu" diyor; suzgecsiz toplamak ss'yi
# 4,38 -> 4,31'e cekiyor ve tez boyunca kullanilan ~4,4 puanlik olcutu bayatlatiyordu.
KOHORT_MAKS_SEED = 29

def band_yukle():
    d = {}
    if os.path.exists(BAND):
        for r in csv.DictReader(open(BAND)):
            s = int(r['seed'])
            if s > KOHORT_MAKS_SEED:   # kohort disi kosum
                continue
            d[(r['rejim'], r['konfig'], s)] = float(r['all_mAP50'])
    return d

def ozet(v):
    if len(v) < 2: return None
    m, s = st.mean(v), st.stdev(v)
    se = s/math.sqrt(len(v))
    t = t_kritik(len(v))
    return dict(n=len(v), ort=round(m*100,2), ss=round(s*100,2),
                ga_alt=round((m-t*se)*100,2), ga_ust=round((m+t*se)*100,2),
                ga_carpan=round(t,4), ga_yontem="t(n-1)",
                min=round(min(v)*100,1), maks=round(max(v)*100,1))

d = band_yukle()
K["_kaynaklar"]["band_csv"] = {"yol": BAND, "md5": sha(BAND)}
if not d:
    K["_uyarilar"] = K.get("_uyarilar", [])
    K["_uyarilar"].append(
        "ARK/ESLI BOLUMLERI URETILMEDI - band CSV bulunamadi (%s). Kayit EKSIKTIR; "
        "dolu bir kaydin uzerine YAZILMAMALIDIR." % BAND)

# --- 1) ARK OZETLERI ---
K["arklar"] = {}
for kon in ("kazanan","taban"):
    for rej in ("map1","252550","333334"):
        v = [x for (r,k,s),x in d.items() if r==rej and k==kon]
        o = ozet(v)
        if o:
            o["durum"] = "TAM" if o["n"]>=30 else "EKSIK(%d/30)"%o["n"]
            o["kaynak"] = "band deneyi · %s · %s" % (rej,kon)
            K["arklar"]["%s_%s"%(kon,rej)] = o

# --- 2) ESLI KARSILASTIRMALAR ---
def esli(a_key, b_key, ad):
    (r1,k1),(r2,k2) = a_key, b_key
    A = {s:x for (r,k,s),x in d.items() if r==r1 and k==k1}
    B = {s:x for (r,k,s),x in d.items() if r==r2 and k==k2}
    ort = sorted(set(A)&set(B))
    if len(ort) < 5: return None
    f = [B[s]-A[s] for s in ort]
    se = st.stdev(f)/math.sqrt(len(f))
    t = t_kritik(len(f))
    res = dict(n=len(ort), fark=round(st.mean(f)*100,2),
               ga_alt=round((st.mean(f)-t*se)*100,2), ga_ust=round((st.mean(f)+t*se)*100,2),
               ga_carpan=round(t,4), ga_yontem="t(n-1)",
               dz=round(st.mean(f)/st.stdev(f),2))
    try:
        from scipy import stats
        res["wilcoxon_p"] = round(stats.wilcoxon(f).pvalue,4)
        res["varyans_orani"] = round(st.variance([B[s] for s in ort])/st.variance([A[s] for s in ort]),2)
        res["levene_p"] = round(stats.levene([A[s] for s in ort],[B[s] for s in ort]).pvalue,4)
    except Exception: pass
    res["kaynak"] = ad
    return res

K["esli"] = {}
for ad,(a,b) in {
    "kazanan_eksi_taban_map1": (("map1","taban"),("map1","kazanan")),
    "252550_eksi_map1_kazanan": (("map1","kazanan"),("252550","kazanan")),
    "333334_eksi_map1_kazanan": (("map1","kazanan"),("333334","kazanan")),
    "252550_eksi_map1_taban":   (("map1","taban"),("252550","taban")),
}.items():
    r = esli(a,b,ad)
    if r: K["esli"][ad] = r

# --- 3) UC REJIM BIRLIKTE (Friedman + Levene) ---
K["rejim_etkisi"] = {}
for kon in ("kazanan","taban"):
    G = {rej:{s:x for (r,k,s),x in d.items() if r==rej and k==kon} for rej in ("map1","252550","333334")}
    ort = sorted(set(G["map1"]) & set(G["252550"]) & set(G["333334"]))
    if len(ort) < 5: continue
    arr = [[G[r][s] for s in ort] for r in ("map1","252550","333334")]
    e = dict(n_tohum=len(ort))
    try:
        from scipy import stats
        fr = stats.friedmanchisquare(*arr)
        e["friedman_chi2"] = round(fr.statistic,2); e["friedman_p"] = round(fr.pvalue,4)
        e["levene_p"] = round(stats.levene(*arr).pvalue,4)
        e["bartlett_p"] = round(stats.bartlett(*arr).pvalue,4)
        sds = [st.stdev(a) for a in arr]
        e["ss_orani_genis_dar"] = round(max(sds)/min(sds),2)
    except Exception: pass
    e["kaynak"] = "band deneyi · %s konfig · 3 rejim eslesmis"%kon
    K["rejim_etkisi"][kon] = e

# --- 4) TEKIL ZIRVE vs BAND ---
kz = [x for (r,k,s),x in d.items() if k=="kazanan"]
kz_map1 = [x for (r,k,s),x in d.items() if k=="kazanan" and r=="map1"]
if kz:
    K["tekil_zirve"] = dict(
        tez_degeri=92.9, n_kosum=len(kz),
        band_ort=round(st.mean(kz)*100,2), band_ss=round(st.stdev(kz)*100,2),
        band_maks=round(max(kz)*100,2),
        ulasan_kosum=sum(1 for v in kz if v>=0.929),
        # IKI AYRI TANIM - hangisinin kullanildigi metinde BELIRTILMELI
        z_tumu=round((0.929-st.mean(kz))/st.stdev(kz),2),
        z_map1=round((0.929-st.mean(kz_map1))/st.stdev(kz_map1),2) if len(kz_map1)>1 else None,
        NOT="z_map1 = 92,9'un KENDI rejiminin (map1, n=30) bandindaki konumu -> TEZDE KULLANILAN. "
            "z_tumu = 90 kosumun tamaminin bandindaki konumu. Metinde hangisi kullanildiysa ACIKCA yazilmali.",
        kaynak="92,9 = tez tab:c3tr-top15 · band = 3 rejim x 30 tohum")

# kohort disi kosumlar - gizlenmez, ayri raporlanir
K["_kohort_disi"] = []
if os.path.exists(BAND):
    for r in csv.DictReader(open(BAND)):
        if int(r['seed']) > KOHORT_MAKS_SEED:
            K["_kohort_disi"].append(dict(rejim=r['rejim'],konfig=r['konfig'],seed=int(r['seed']),
                                          deger=float(r['all_mAP50']),makine=r.get('makine','?')))

# --- 5) 256-IZGARA (768 model = 256 mimari x 3 rejim) ---
# DUZELTME (04.09): bu bolum izgarayi TEZIN EKINDEN (ek2.tex) ayristiriyordu. Kanonik
# kayit boylece tezden turuyordu => DONGUSEL: tez kendi kendini dogrular duruma dusuyordu.
# Artik ham kosum ciktisindan (C3TR_kanonik_768.csv, 3072 satir) uretiliyor. Tez ekine
# yalnizca DOGRULAMA icin bakilir, kaynak olarak degil.
#
# Dilim secimi: ham CSV her modeli 4 kez tasir (conf {0,001; 0,25} x iou {0,5; 0,6}).
# Tez ekindeki degerleri veren dilim CONF 0,001 / IOU 0,5'tir; olculdu, 768/768 model
# dort sutunda da birebir esledi (P/R/mAP50 sapma 0,0000 · F1 <=0,005 yuvarlama).
# DUZELTME (05.09, 910): dosya yalniz OUT'ta aranirsa, betik kanonik konumundan
# kosuldugunda (CSV orada yok) izgara bolumu SESSIZCE atlaniyordu — 155'in 05.09 00:00
# kosumunda tam bu oldu, kayit izgarasiz uretildi ve kimse fark etmedi.
# Artik birden cok konum taranir VE bulunamazsa _uyarilar'a yazilir.
# DUZELTME (18.10, Mac-inceleme'nin mutlak-yol taramasi uzerine): aday listesi
# veri/ dizinini ICERMIYORDU, oysa dosya 26.09'dan beri veri/C3TR_kanonik_768.csv
# olarak DEPODA (3073 satir). Sonuc: izgara blogu kayitta HIC YOKTU ve yerine
# "IZGARA URETILMEDI - ham CSV bulunamadi" uyarisi duruyordu. Yani uyari dogruydu
# (betik bulamamisti) ama NEDENI yanlisti (dosya kaybolmamis, liste eksikti).
# Mac mutlak yollarin OKUNAMAZLIGINI bildirdi; tarama ayni alanda ISLEVSEL bir
# kusur ortaya cikardi -- uyari metnindeki uc yol, aramanin NEREYE BAKMADIGINI
# gosteriyordu.
_ham_adaylari = [os.path.join(OUT, "..", "veri", "C3TR_kanonik_768.csv"),
                 os.path.join(OUT, "C3TR_kanonik_768.csv"),
                 os.path.join(OUT, "..", "kanonik_kaynak", "C3TR_kanonik_768.csv"),
                 os.path.join(OUT, "..", "..", "_KOORDINASYON", "kanonik_kaynak", "C3TR_kanonik_768.csv")]
HAM = next((os.path.normpath(a) for a in _ham_adaylari if os.path.exists(a)), _ham_adaylari[0])
IZGARA_CONF, IZGARA_IOU = "0.001", "0.5"
# CSV rejim adi -> kayit anahtari (onceki ek2 anahtarlariyla ayni tutuldu, tuketiciler kirilmasin)
REJIM_ADI = {"regime_25-25-50": "252550", "regime_33-33-34": "333334", "regime_map1": "map1"}
# Blok adlandirmasi: ham kosumlar 'cv', tez eki 'c3' yaziyor - AYNI blok, farkli etiket.
def _konfig_adi(model_yolu):
    return model_yolu.split("/")[-1].replace("cv", "c3")

if not os.path.exists(HAM):
    K["_uyarilar"] = K.get("_uyarilar", [])
    K["_uyarilar"].append(
        "IZGARA URETILMEDI - ham CSV bulunamadi. Arananlar: %s. "
        "Kayit EKSIKTIR; C3TR_kanonik_768.csv betigin yanina konup yeniden kosulmalidir."
        % " | ".join(os.path.normpath(a) for a in _ham_adaylari))

if os.path.exists(HAM):
    K["_kaynaklar"]["izgara_ham"] = {"yol": HAM, "md5": sha(HAM),
                                     "dilim": "conf=%s iou=%s" % (IZGARA_CONF, IZGARA_IOU),
                                     "not": "ham kosum ciktisi - TEZDEN TURETILMEMISTIR"}
    izgara = {}
    for r in csv.DictReader(open(HAM, encoding="utf-8")):
        if r["conf"] != IZGARA_CONF or r["iou"] != IZGARA_IOU:
            continue
        rej = REJIM_ADI.get(r["regime"])
        if rej is None:
            continue
        izgara.setdefault(rej, {})[_konfig_adi(r["model"])] = dict(
            P=round(float(r["all_P"]) * 100, 1), R=round(float(r["all_R"]) * 100, 1),
            mAP50=round(float(r["all_mAP50"]) * 100, 1), F1=round(float(r["all_F1"]) * 100, 1))
    K["izgara"] = {r: v for r, v in izgara.items() if v}
    K["izgara_ozet"] = {}
    for r, v in K["izgara"].items():
        vals = [x["mAP50"] for x in v.values()]
        if len(vals) > 1:
            en_iyi = max(v.items(), key=lambda kv: kv[1]["mAP50"])
            en_kotu = min(v.items(), key=lambda kv: kv[1]["mAP50"])
            K["izgara_ozet"][r] = dict(
                n=len(vals), ort=round(st.mean(vals), 2), ss=round(st.stdev(vals), 2),
                min=min(vals), maks=max(vals),
                en_iyi=en_iyi[0], en_kotu=en_kotu[0],
                kaynak="ham kosum ciktisi C3TR_kanonik_768.csv (conf %s / iou %s)" % (IZGARA_CONF, IZGARA_IOU))

# --- 5b) DOGRULAMA: uretilen izgara tez ekiyle ortusuyor mu? ---
# Yon onemli: ek2.tex burada KAYNAK degil, SINAMA hedefidir. Ayrisma varsa tez ile ham
# veri arasinda gercek bir sapma var demektir; sessizce gecilmemeli.
_ek2_adaylari = [os.path.join(OUT, "ek2.tex"),
                 os.path.join(OUT, "..", "..", "ek2.tex"),
                 os.path.join(OUT, "..", "ek2.tex")]
EK2 = next((os.path.normpath(a) for a in _ek2_adaylari if os.path.exists(a)), _ek2_adaylari[0])
if K.get("izgara") and os.path.exists(EK2):
    metin = io_open(EK2)
    tez_izgara = {}
    aktif = None
    for satir in metin.split("\n"):
        et = re.search(r"\\label\{tab:([0-9a-z-]+)-test-sonuclari\}", satir)
        if et:
            aktif = et.group(1); tez_izgara.setdefault(aktif, {}); continue
        if aktif is None:
            continue
        for mm in re.finditer(
            r"backbone\\_([a-z0-9-]+)\\ head\\_([a-z0-9-]+)\s*&\s*([0-9,]+)\s*&\s*([0-9,]+)\s*&\s*([0-9,]+)\s*&\s*([0-9,]+)", satir):
            f = lambda x: float(x.replace(",", "."))
            tez_izgara[aktif]["backbone_%s_head_%s" % (mm.group(1), mm.group(2))] = dict(
                P=f(mm.group(3)), R=f(mm.group(4)), mAP50=f(mm.group(5)), F1=f(mm.group(6)))
    ayrisan = []
    karsilastirilan = 0
    for rej, v in K["izgara"].items():
        for ad, deger in v.items():
            tez = tez_izgara.get(rej, {}).get(ad)
            if tez is None:
                continue
            for alan in ("P", "R", "mAP50", "F1"):
                karsilastirilan += 1
                if abs(tez[alan] - deger[alan]) > 0.051:
                    ayrisan.append(dict(rejim=rej, konfig=ad, alan=alan,
                                        tez=tez[alan], ham=deger[alan]))
    # DUYARLIK BEYANI (18.10, Mac-inceleme): "ORTUSUYOR" sozcugu olculenden fazlasini
    # soyluyordu. Izgara degerleri kayitta BIR ONDALIKLA duruyor (6144 float'in tamami
    # 1 basamak) ve ek2.tex de bir ondalik tasiyor; dolayisiyla "ayrisan 0" yalniz BIR
    # ONDALIK duyarlikta kurulmustur, ham duyarlikta SINANMAMISTIR. Bu, ayni gun iki kez
    # yasadigimiz hatanin kardesi: varyans kimliginin "birebir kapandigi" iki ondalikta
    # dogrulanmisti, kalinti 3,83e-05 cikti. Ham duyarlikta sinama ek2.tex ile MUMKUN
    # DEGIL (o da bir ondalik tasiyor); bu nedenle eksiklik gizlenmez, BEYAN EDILIR.
    K["_izgara_dogrulama"] = dict(
        karsilastirilan=karsilastirilan, ayrisan=len(ayrisan), ornekler=ayrisan[:20],
        duyarlik="bir ondalik (kayit ve ek2.tex ikisi de 1 basamak tasiyor)",
        ham_duyarlikta_sinandi_mi=False,
        sonuc=("BIR ONDALIK DUYARLIKTA ORTUSUYOR; ham duyarlikta sinanmadi"
               if not ayrisan else "AYRISMA VAR - INCELE"),
        not_="ek2.tex burada kaynak degil sinama hedefidir; kayit ham veriden uretilir")


# ==================== KANONIK v2 (26.09) — secim korlugu + sinif bazli ====================
import collections as _col
def _f2(x):
    try: return float(x)
    except Exception: return None
# --- 6) SECIM KORLUGU: doyma (PLATO) + best/last (BVL) ---
_C = os.path.join(OUT, "..")
PLATO = _ilk_var(os.environ.get("PLATO_CSV"),
                 os.path.join(_C, "_910_PLATO_KOHORT_HAM_20260910.csv"),
                 os.path.join(OUT, "_910_PLATO_KOHORT_HAM_20260910.csv"),
                 "/media/dnnlab2/SamsungSSD/makale_atolyesi/kanonik/_910_PLATO_KOHORT_HAM_20260910.csv")
BVL = _ilk_var(os.environ.get("BVL_CSV"),
               os.path.join(_C, "_910_BEST_VS_LAST_20260910.csv"),
               os.path.join(OUT, "_910_BEST_VS_LAST_20260910.csv"),
               "/media/dnnlab2/SamsungSSD/makale_atolyesi/kanonik/_910_BEST_VS_LAST_20260910.csv")
EK6 = _ilk_var(os.environ.get("EK6_CSV"),
               os.path.join(_C, "_910_EK6_504_sinif_bazli_20260910.csv"),
               os.path.join(OUT, "_910_EK6_504_sinif_bazli_20260910.csv"),
               "/media/dnnlab2/SamsungSSD/makale_atolyesi/kanonik/_910_EK6_504_sinif_bazli_20260910.csv")
K["secim_korlugu"] = {}
if os.path.exists(PLATO):
    K["_kaynaklar"]["plato_csv"] = {"yol": PLATO, "md5": sha(PLATO)}
    _pr = [r for r in csv.DictReader(open(PLATO)) if r.get("durum") == "OK" and r.get("birlesik") == "False"]
    _doyma = {}
    for _aile in sorted(set(r["aile"] for r in _pr)):
        for _ep in (1000, 3000, 6000):
            _v = [float(r["egitim_tepe_mAP50"]) for r in _pr if r["aile"] == _aile and int(r["epoch"]) == _ep]
            if _v:
                _doyma["%s_%d" % (_aile, _ep)] = dict(n=len(_v),
                    ss=round(st.pstdev(_v) if len(_v) > 1 else 0.0, 6),
                    benzersiz=len(set(round(x, 4) for x in _v)),
                    ort=round(st.mean(_v), 4),
                    ust099=round(100 * sum(1 for x in _v if x > 0.99) / len(_v), 1))
    K["secim_korlugu"]["doyma_aile_epok"] = _doyma
    K["secim_korlugu"]["doyma_ozet"] = ("ULTRALYTICS 3000 ve 6000 epok: ss=0,000000 tek deger 0,995 (tam sabit; "
        "secim olcutu ayirt edici degiskenlik tasimiyor); 1000 epok ~%95 >0,99. v7 6000'de yakinsiyor (~%96), "
        "v4 ayri dusuk aile (~0,60). COK KAYNAK: PLATO CSV + 910 disk-scan 420 hucre + 155 raw results.csv.")
else:
    K.setdefault("_uyarilar", []).append("PLATO CSV yok (%s) - doyma blogu uretilmedi" % PLATO)
if os.path.exists(BVL):
    K["_kaynaklar"]["bvl_csv"] = {"yol": BVL, "md5": sha(BVL)}
    _B = list(csv.DictReader(open(BVL)))
    _allf = [float(r["fark_puan"]) for r in _B if r.get("fark_puan")]
    _bl = dict(n=len(_allf), ortanca_puan=round(st.median(_allf), 3),
               yuzde_lehte=round(100 * sum(1 for x in _allf if x > 0) / len(_allf), 1))
    try:
        from scipy import stats as _s
        _bl["wilcoxon_p"] = round(_s.wilcoxon(_allf).pvalue, 4)
    except Exception:
        pass
    _bl["epok_ortanca"] = {}
    for _ep in (1000, 3000, 6000):
        _v = [float(r["fark_puan"]) for r in _B if int(r["epoch"]) == _ep]
        if _v: _bl["epok_ortanca"][str(_ep)] = round(st.median(_v), 3)
    _bl["kaynak"] = "best.pt vs last.pt test mAP@0,5 farki (puan). Hikaye epoga gore SONUM: 1000 lehte, 3000/6000 sifir."
    K["secim_korlugu"]["best_last"] = _bl
else:
    K.setdefault("_uyarilar", []).append("BVL CSV yok (%s) - best/last blogu uretilmedi" % BVL)
# --- 7) SINIF BAZLI: asimetri + rho + epok-sinif etkisi ---
if os.path.exists(EK6):
    K["_kaynaklar"]["ek6_sinif_csv"] = {"yol": EK6, "md5": sha(EK6)}
    _E = list(csv.DictReader(open(EK6)))
    _sb = {"n_hucre": len(_E), "n_model": len(set(r["ek6_ad"] for r in _E)),
           "koken_uyarisi": "mAP sutunlari ek6 yayimlanmis; K/D sutunlari 910 yeniden-olcum; v7 protokol karisik; 4 hucrede K/D belirsiz. mAP tabanli grafik guvenli."}
    _gaps = [_f2(r.get("ek6_mAP50_kotu")) - _f2(r.get("ek6_mAP50_iyi")) for r in _E
             if _f2(r.get("ek6_mAP50_kotu")) is not None and _f2(r.get("ek6_mAP50_iyi")) is not None]
    _sb["asimetri"] = dict(n=len(_gaps), pozitif=sum(1 for g in _gaps if g > 0),
        ort_puan=round(st.mean(_gaps) * 100, 1),
        not_="malign(kotu) hep benign(iyi) ustunde. Tezde bolum3:293'te ZATEN VAR - TEYIT, yeni bulgu degil.")
    try:
        from scipy import stats as _s
        _tr = [(_f2(r.get("ek6_mAP50")), _f2(r.get("ek6_mAP50_iyi")), _f2(r.get("ek6_mAP50_kotu"))) for r in _E]
        _tr = [t for t in _tr if None not in t]
        _A = [x[0] for x in _tr]; _I = [x[1] for x in _tr]; _Kk = [x[2] for x in _tr]
        _sb["rho"] = dict(genel_iyi=round(_s.spearmanr(_A, _I).correlation, 3),
            genel_kotu=round(_s.spearmanr(_A, _Kk).correlation, 3),
            kotu_iyi=round(_s.spearmanr(_Kk, _I).correlation, 3),
            kotu_iyi_p=round(_s.spearmanr(_Kk, _I).pvalue, 3),
            not_="kotu_iyi BAGIMSIZLIK DEGIL (fazla soylem; p=0,10 sifiri reddetmiyor ama bagimsizlik kaniti degil). Asil kontrast: genel-iyi(0,90) >> genel-kotu(0,46) => genel mAP siralamasi buyuk olcude BENIGN siralamasi.")
        _cell = _col.defaultdict(dict)
        for r in _E:
            _cell[(r["ek6_ad"], r["ImageSize"])][int(r["epoch"])] = (_f2(r.get("ek6_mAP50_iyi")), _f2(r.get("ek6_mAP50_kotu")))
        _me = _col.defaultdict(lambda: {"i": [], "k": []})
        for _key, _ep in _cell.items():
            if 6000 in _ep and 1000 in _ep and None not in _ep[6000] + _ep[1000]:
                _me[_key[0]]["i"].append(_ep[6000][0] - _ep[1000][0]); _me[_key[0]]["k"].append(_ep[6000][1] - _ep[1000][1])
        _iyi = [st.mean(v["i"]) for v in _me.values() if v["i"]]; _kotu = [st.mean(v["k"]) for v in _me.values() if v["k"]]
        if _iyi:
            _sb["epok_sinif_etkisi"] = dict(kontrast="6000 eksi 1000 epok", n_model=len(_iyi),
                iyi_ort_puan=round(st.mean(_iyi) * 100, 2), iyi_pozitif=sum(1 for x in _iyi if x > 0), iyi_p=float("%.2g"%_s.wilcoxon(_iyi).pvalue),
                kotu_ort_puan=round(st.mean(_kotu) * 100, 2), kotu_pozitif=sum(1 for x in _kotu if x > 0), kotu_p=float("%.2g"%_s.wilcoxon(_kotu).pvalue),
                not_="MODEL duzeyi (n=43); hucre duzeyi (n=168) SOZDE-YINELEME (ayni model 4 cozunurlukte). Epok artinca BENIGN iyilesir, MALIGN geriler (ters etki).")
    except Exception as _e:
        _sb["_hata"] = "scipy/hesap: %s" % _e
    K["sinif_bazli"] = _sb
else:
    K.setdefault("_uyarilar", []).append("EK6 sinif CSV yok (%s) - sinif_bazli blogu uretilmedi" % EK6)
# ==================== /KANONIK v2 ====================

# ============================================================================
# EK BLOKLAR (155, 17.10.2026) — EK-82/EK-83/EK-85'in olcumleri kanonik kayda
# girer. Gerekce: ISLEYIS.md Katman 0 "bu kayitta olmayan sayi makalede
# kullanilamaz" kurali; 17.10 denetiminde S3.3'un yeni sayilarinin kayit disinda
# oldugu bulundu (Mac-inceleme bagimsiz gecisi, bulgu [A]).
# Elle yazilmaz: asagidaki her deger kaynak CSV'den HESAPLANIR.
# ============================================================================
_V = os.path.join(os.path.dirname(OUT), "veri")

def _depo_rel(y):
    """Depo-goreli adres. Blok 'kaynak' alanlari bunu kullanir: mutlak yol arsivi
    indiren okurda cozulmez (Mac-inceleme 18.10)."""
    try:
        _k = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(y)),
                             "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True).stdout.strip()
        if _k:
            _r = os.path.relpath(os.path.abspath(y), _k)
            if not _r.startswith(".."): return _r
    except Exception:
        pass
    return y

def _oku(ad):
    y = os.path.join(_V, ad)
    if not os.path.exists(y): return None, None
    with open(y, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f)), y

def _pearson(x, y):
    n = len(x); mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((i-mx)**2 for i in x)); sy = math.sqrt(sum((i-my)**2 for i in y))
    return sum((i-mx)*(j-my) for i, j in zip(x, y))/(sx*sy) if sx and sy else None

def _sira(xs):
    s = sorted(range(len(xs)), key=lambda i: -xs[i]); r = [0]*len(xs)
    for k, i in enumerate(s): r[i] = k+1
    return r

def _spearman(a, b):
    ra, rb = _sira(a), _sira(b); n = len(a)
    d = sum((ra[i]-rb[i])**2 for i in range(n))
    return 1 - 6*d/(n*(n*n-1))

# --- BLOK 1: parti-eslenmis ayristirma kolu (EK-82) -------------------------
_r, _y = _oku("_ayristirma30_sgd_b8_155_20261015.csv")
if _r:
    K["_kaynaklar"]["ayristirma30"] = {"yol": _y, "md5": sha(_y)}
    t = {int(x["tohum"]): (100*float(x["mAP50"]), 100*float(x["AP_malign"]), 100*float(x["AP_benign"])) for x in _r}
    g = [t[k][0] for k in sorted(t)]; m = [t[k][1] for k in sorted(t)]; b = [t[k][2] for k in sorted(t)]
    s0 = t[0]; oth = [t[k][0] for k in t if k != 0]
    rg, rm, rb = _sira(g), _sira(m), _sira(b)
    i0 = sorted(t).index(0)
    vm, vb = st.variance(m), st.variance(b)
    cov = sum((m[i]-st.mean(m))*(b[i]-st.mean(b)) for i in range(len(m)))/(len(m)-1)
    vg = st.variance(g); vg_hesap = (vm+vb+2*cov)/4
    ort = {}
    for kk in (1, 3, 5):
        sg = {i for i in range(len(g)) if rg[i] <= kk}
        ort["en_iyi_%d" % kk] = {"genel_kesisim_benign": len(sg & {i for i in range(len(b)) if rb[i] <= kk}),
                                 "genel_kesisim_malign": len(sg & {i for i in range(len(m)) if rm[i] <= kk})}
    K["ayristirma_kolu"] = {
        "tanim": "sampiyonun cozulmus yapilandirmasi, toplu is boyutu 8'e SABIT, 30 tohum, Kohort B'nin makinesinde (dnnlab3)",
        "n": len(g), "ort": round(st.mean(g), 4), "ss": round(st.stdev(g), 4),
        "medyan": round(st.median(g), 4), "min": round(min(g), 4), "maks": round(max(g), 4),
        "sampiyon": {"deger": round(s0[0], 6), "sira_genel": rg[i0],
                     "malign": round(s0[1], 6), "sira_malign": rm[i0],
                     "benign": round(s0[2], 6), "sira_benign": rb[i0]},
        "sampiyon_disi_29": {"n": len(oth), "ort": round(st.mean(oth), 4), "ss": round(st.stdev(oth), 4),
                             "maks": round(max(oth), 4),
                             "z_sampiyon": round((s0[0]-st.mean(oth))/st.stdev(oth), 4),
                             "ustunde_kosum": sum(1 for v in oth if v >= s0[0])},
        "sinif": {"malign_ort": round(st.mean(m), 4), "malign_ss": round(st.stdev(m), 4),
                  "benign_ort": round(st.mean(b), 4), "benign_ss": round(st.stdev(b), 4)},
        "varyans_ayrisimi": {"birim": "puan^2", "kimlik": "Var(genel)=[Var(mal)+Var(ben)+2Cov]/4",
                             "var_malign": round(vm, 4), "var_benign": round(vb, 4), "kovaryans": round(cov, 4),
                             "var_genel_hesaplanan": round(vg_hesap, 4), "var_genel_olculen": round(vg, 4),
                             "kimlik_artik": round(vg_hesap-vg, 9),
                             "kimlik_kapandi": abs(vg_hesap-vg) < 1e-3,
                             "esik_gerekcesi": "CSV 6 haneye yuvarli; 100x olcekte yuvarlama 1e-4 puan -> varyansta ~1e-5 puan^2. Esik 1e-3 bu mertebenin iki kat ustunde secildi. Cebirsel kimlik TAM; artik yalniz yuvarlamadandir.",
                             "pay_benign_yuzde": round((vb/4)/vg*100, 2),
                             "pay_malign_yuzde": round((vm/4)/vg*100, 2),
                             "pay_kovaryans_yuzde": round((2*cov/4)/vg*100, 2)},
        "korelasyon": {"birim": "kosum", "n": len(g),
                       "pearson_genel_benign": round(_pearson(g, b), 4),
                       "pearson_genel_malign": round(_pearson(g, m), 4),
                       "spearman_genel_benign": round(_spearman(g, b), 4),
                       "spearman_genel_malign": round(_spearman(g, m), 4),
                       "not_": "BIRIM KOSUM (n=30). sinif_bazli.rho ise 504 HUCRE uzerinde; iki buyukluk ayridir, karsilastirilmaz."},
        "sira_ortusmesi": ort,
        "kaynak": _depo_rel(_y),
        "not_": "EK-82. Kanonik sinif_bazli.rho notu 504 hucre duzeyinde 'genel siralama buyuk olcude benign siralamasi' demisti; bu blok ayni olguyu 30 KOSUM duzeyinde niceler (varyans payi + sira ortusmesi). Yeni bulgu degil, nicelemedir.",
    }

# --- BLOK 2: capraz makine (EK-85) -----------------------------------------
_r2, _y2 = _oku("_capraz_makine_155_20261016.csv")
if _r2:
    K["_kaynaklar"]["capraz_makine"] = {"yol": _y2, "md5": sha(_y2)}
    d = {x["kosum"]: x for x in _r2}
    a, c = d.get("dnnlab3_sampiyon"), d.get("155_caprazmakine")
    if a and c:
        K["capraz_makine"] = {
            "tanim": "ayni yapilandirma + ayni tohum + ayni kart modeli (RTX 2080 Ti) + ayni ultralytics 8.3.63 + BAYT-AYNI veri; fark yalniz fiziksel makine ve CUDA derlemesi (cu118 vs cu121)",
            "eksen_ayristirilabilir_mi": False,
            "eksen_notu": ("makine ile CUDA derlemesi BIRLIKTE degisiyor; iki etken ayristirilamaz"),
        "UCUNCU_ETKEN_UYARISI": {
            "bulgu": ("SURUCU SURUMU bu olcumun HER IKI UCUNDA DA KAYITLI DEGIL. CSV'de surucu "
                      "kolonu yok (kolonlar: kosum, mAP50, mAP5095, P, R, AP_malign, AP_benign) "
                      "ve kosum kutuklerinde surucu kaydi bulunamadi -- kutukler yalniz "
                      "Python/torch surumunu tasiyor."),
            "sonuc": ("Dolayisiyla 'iki etken' ifadesi EKSIK olabilir: eksen makine + CUDA "
                      "derlemesi + SURUCU tasiyor olabilir ve ucuncusu DISLANAMAZ. Kayitta "
                      "olmayan bir etkenin yoklugu iddia edilemez."),
            "E2_TABLOSU_TASINAMAZ": ("19.10'da E2 icin olculen surucu tablosu (155: 570.124.04 · "
                                     "dnnlab3: 525.125.06 · 910: 520.61.05 · 475: 470.256.02) BU "
                                     "OLCUMU TARIF ETMEZ: E2 yigini torch 2.4.1, M3 yigini "
                                     "torch 2.2.2+cu118 / ultralytics 8.3.63, ve olcum tarihleri "
                                     "ayri (16.10 ↔ 19.10). Baska bir deneyin donanim tablosunu "
                                     "buraya tasimak, gun icinde uc kez curuttugumuz hatanin "
                                     "aynisi olurdu."),
            "nasil_kapanir": ("yeniden olcumde surucu surumu CSV kolonu olarak kaydedilir "
                              "(dnnlab3 kuyrugundaki IS 1 ve IS 2 bu sarti tasiyor)"),
            "GERIYE_DONUK_ATIF_21_10": {
                "yontem": ("910'un 21.10 bulgusu: surucu surumu KOSUM ANINDA kaydedilmemis olsa "
                           "da DOLAYLI olarak atfedilebilir. Iki bagimsiz iz: (a) surum-adli modul "
                           "dosyasinin mtime'i, (b) paket yoneticisi kutuklerinin ilgili penceredeki "
                           "sessizligi. Kurtarilamaz olan surucunun kendisi degil, o anda hangisinin "
                           "yuklu oldugunun KAYDI."),
                "olcum_tarihi": "2026-10-16 (veri/_capraz_makine_155_20261016.csv)",
                "uc_155": {
                    "surucu": "570.124.04",
                    "modul_mtime": "2025-03-05 22:29 (libnvidia-glcore.so.570.124.04, x86_64 ve i386)",
                    "paket_izi": ("apt history 2025-03-05 22:09:14 'apt-get purge nvidia-*'; modul "
                                  "dosyalari 22:29'da yazilmis -> .run yukleyicisiyle kurulum, dpkg'de "
                                  "install satiri olmamasinin nedeni bu. TUM dpkg kutuklerinde "
                                  "(sikistirilmis dahil) nvidia install/upgrade satiri: 0. 2025-03-05 "
                                  "sonrasi herhangi bir nvidia hareketi: YOK."),
                    "libnvidia_mtime_kumesi": ["2022-09-29 (eski 520 kalintisi)", "2025-03-05 (570 kurulumu)"],
                    "hukum": "570.124.04 2025-03-05'ten beri kesintisiz -> 16.10.2026 olcumunu KAPSIYOR",
                },
                "uc_dnnlab3": {
                    "surucu": "525.125.06",
                    "modul_mtime": "2023-05-30 (i386 07:59, x86_64 08:37)",
                    "paket_izi": ("son nvidia paket hareketi 2023-07-10 11:11:07 'Upgrade: "
                                  "libnvidia-compute-515 -> 525.125.06'. nvidia install/upgrade olan "
                                  "gunler: 2022-10-03, 2023-01-06, 2023-05-30, 2023-06-16, 2023-07-03, "
                                  "2023-07-10. 2026-10-16 sonrasi hareket: YOK."),
                    "hukum": "525.125.06 en gec 2023-07-10'dan beri kesintisiz -> 16.10.2026 olcumunu KAPSIYOR",
                },
                "SONUC": ("UCUNCU ETKEN DISLANAMAZ DEGIL -- VAR VE OLCULU. Iki ucun surucusu FARKLI: "
                          "155 570.124.04 ↔ dnnlab3 525.125.06. Eksen UC etken tasiyor: (1) fiziksel "
                          "makine, (2) CUDA derlemesi cu118 ↔ cu121, (3) surucu surumu. Ucu de BIRLIKTE "
                          "degisiyor ve n=1 ile ayristirilamaz."),
                "artik_belirsizlik": ("`.run` ile zaman damgasini KORUYAN bir yeniden kurulum teorik "
                                      "olarak mumkundur ve mtime'i degistirmez. Iki ucta da mtime buna "
                                      "karsi kanit ama mutlak degil; kanit sinifi cagdas_kayit ustu, "
                                      "kolon_ayirt_edici DEGIL."),
                "kapanmayan": ("475'in s22 kolu (iskarta) ve kart modeli ekseni ayridir. Bu atif M3 "
                               "yigini icin kuruldu; ustteki E2_TABLOSU_TASINAMAZ gecerliligini korur."),
            },
        },
            "dnnlab3_mAP50": float(a["mAP50"]), "mak155_mAP50": float(c["mAP50"]),
            "fark_puan": round(100*(float(a["mAP50"])-float(c["mAP50"])), 4),
            "malign_fark_puan": round(100*(float(a["AP_malign"])-float(c["AP_malign"])), 4),
            "benign_fark_puan": round(100*(float(a["AP_benign"])-float(c["AP_benign"])), 4),
            "tensor_ayni_ayni_makine": "937/937", "tensor_ayni_capraz_makine": "162/937",
            "n_yineleme": 1,
            "kaynak": _depo_rel(_y2),
            "not_": "EK-85. TEK yineleme: acikligin VARLIGI kurulur, BUYUKLUGU kurulmaz. Eslesen 162 tensor dejenere (donmus BN, sabit DFL cekirdegi, tamsayi sayaclar); ogrenilmis tensorde eslesme yok.",
        }

# --- BLOK 3: cozulen optimizer denetimi (EK-80) ----------------------------
_r3, _y3 = _oku("_504_cozulen_optimizer_155_20261013.csv")
if _r3:
    K["_kaynaklar"]["cozulen_optimizer"] = {"yol": _y3, "md5": sha(_y3)}
    ist = _col.Counter(x.get("optimizer_istenen") or "yok" for x in _r3)
    coz = _col.Counter(x.get("optimizer_cozulen") or "yok" for x in _r3)
    auto_epok = _col.Counter(str(x.get("epoch")) for x in _r3 if x.get("optimizer_istenen") == "auto")
    K["cozulen_optimizer"] = {
        "n_hucre": len(_r3),
        "istenen": dict(ist), "cozulen": dict(coz),
        "auto_hucre_epok_dagilimi": dict(auto_epok),
        "momentum_sapmasi": {"n_hucre": ist.get("auto", 0), "beyan": 0.937, "gercek": 0.9,
                             "gerekce": "auto dali momentumu 0,9'a zorlar (ultralytics 8.3.63 trainer.py); beyan edilen 0,937 o hucrelerde kullanilmamistir"},
        "kaynak": _depo_rel(_y3),
        "not_": "EK-80. optimizer:auto yazan hucrelerin TAMAMI 6000 epoktadir ve SGD'ye cozulur; 1000/3000 epokta auto YOKTUR.",
    }



# --- BLOK 4: belirlenimcilik ve sampiyon cifti (EK-81/EK-83) ----------------
# Kaynaklar: sampiyonun yeniden olculen degeri capraz_makine CSV'sinde,
# Kohort B seed00 ise seed30_yolov9c CSV'sinde (conf 0,001 / IoU 0,5 satiri).
_rb, _yb = None, os.path.join(_V, "seed30_yolov9c_20260728.csv")
if os.path.exists(_yb):
    with open(_yb, newline="", encoding="utf-8") as f:
        _rb = [x for x in csv.DictReader(f) if x.get("Conf") == "0.001" and x.get("IoU") == "0.5"]
if _rb and K.get("capraz_makine"):
    K["_kaynaklar"]["kohortB_seed30"] = {"yol": _yb, "md5": sha(_yb)}
    _kb0 = next((x for x in _rb if int(x["seed"]) == 0), None)
    _kbh = [100*float(x["mAP50"]) for x in _rb]
    if _kb0:
        _s_yeni = 100*K["capraz_makine"]["dnnlab3_mAP50"]
        _s_kb0 = 100*float(_kb0["mAP50"])
        K["belirlenimcilik"] = {
            "tanim": "YOLOv9-c 640/1000 hucresi: ayni yapilandirma + ayni tohum (0) + ayni makine (dnnlab3) + ayni surum (8.3.63) ile UC kosum",
            "sampiyon_yeniden_olculen": round(_s_yeni, 6),
            "kohortB_seed00": round(_s_kb0, 6),
            "cift_farki_puan": round(_s_yeni - _s_kb0, 4),
            "kohortB_dagilimi": {"n": len(_kbh), "ort": round(st.mean(_kbh), 4), "ss": round(st.stdev(_kbh), 4),
                                 "maks": round(max(_kbh), 4),
                                 "not_": "Kohort B toplu is boyutu AutoBatch'e birakilmis: 8/7/6 olarak 1/6/23 tohumda cozulmustur"},
            "bayt_aynilik": {"gozlenen_kosum": 3, "ayni": 2, "ayrisik": 1, "oran": "2/3",
                             "tensor_ayni_makine": "937/937", "tensor_capraz_makine": "162/937",
                             "not_": "ORAN KESTIRILEMEZ: n=3. 'oran 2/3' oldugu gibi bildirilir, siklik iddiasi yapilmaz. n>=5 olcumu tamamlanmadi."},
            "dislanan_adaylar": [
                {"aday": "kayitli yapilandirma", "gerekce": "92/92 alan ckpt train_args + args.yaml'dan okundu", "gerekce_turu": "pozitif_olcum"},
                {"aday": "cozulmus toplu is boyutu", "gerekce": "ckpt train_args.batch=8 ucunde de", "gerekce_turu": "pozitif_olcum"},
                {"aday": "AutoBatch bellek yoklamasi", "gerekce": "sampiyon da batch:-1 ile kostu; yeni kol sabit 8 ile kostu ve BAYT-AYNI cikti (karsit kosum)", "gerekce_turu": "pozitif_olcum"},
                {"aday": "egitim verisi", "gerekce": "labels.jpg md5 ortustu (c171c876)", "gerekce_turu": "pozitif_olcum"},
                {"aday": "baslangic agirliklari", "gerekce": "epok 1 dogrulama kayiplari ucunde ayni", "gerekce_turu": "pozitif_olcum"},
                {"aday": "karisik duyarlik (AMP)", "gerekce": "bit-ozdes dokuz ciftin args.yaml'inda amp:true okundu; sampiyon hucresiyle ayni", "gerekce_turu": "pozitif_olcum"},
                {"aday": "etiket onbellegi (labels.cache)", "gerekce": "iki mekanizma olculdu: dosya sirasi md5 ayni (48653e13e591) ve dataset kurulduktan sonra random/numpy/torch durumlari ayni", "gerekce_turu": "pozitif_olcum"},
            ],
            "kalan_aciklama": "calisma zamani nondeterminizmi; kok neden tekil bir isleme indirgenemedi",
            "h87_denetimi": "yedi dislamanin yedisi POZITIF OLCUM; hicbiri 'bulamadim' turu yokluk cikarimi degil",
            "kaynak": [_depo_rel(_yb), K["capraz_makine"]["kaynak"]],
            "not_": "EK-81 + EK-83. Cift farki, sampiyonun YENIDEN OLCULEN degeriyle (0,799009) hesaplanir; izgarada kayitli deger (0,801) ile hesaplanirsa 11,6 cikar ve bu ayrim metinde beyan edilmistir.",
        }


# ============================================================================
# DENETIM TURU 17.10 (dort mercekli denetim + Mac-inceleme bagimsiz denetimi).
# Katman 0 kurali: "bu kayitta olmayan sayi makalede kullanilamaz." Asagidaki bes
# buyukluk taslakta KULLANILIYORDU ama kayitta YOKTU; kayda aliniyor.
# ============================================================================

def _f(x):
    try: return float(x)
    except Exception: return None

# --- [1] KOHORT C (tipik yapilandirma; izgaranin KENDI ardisik duzeni) --------
# Bulgu #7: §3.1 aile kiyasina Kohort A'nin bandini (4,4) baglamisti; izgaranin
# kendi ardisik duzeninin bandi Kohort C'dir. Iki kohort ayri olcumdur.
_rc, _yc = _oku("seed30_yolov5s_surumkohortu_20260730.csv")
if _rc:
    _v = [_f(x["mAP50"])*100 for x in _rc
          if abs((_f(x.get("Conf")) or -1)-0.001)<1e-9 and abs((_f(x.get("IoU")) or -1)-0.5)<1e-9]
    _vm = [_f(x["mAP50m"])*100 for x in _rc
           if abs((_f(x.get("Conf")) or -1)-0.001)<1e-9 and abs((_f(x.get("IoU")) or -1)-0.5)<1e-9]
    _vb = [_f(x["mAP50b"])*100 for x in _rc
           if abs((_f(x.get("Conf")) or -1)-0.001)<1e-9 and abs((_f(x.get("IoU")) or -1)-0.5)<1e-9]
    if _v:
        K["kohort_C"] = {
            "tanim": "Kohort C -- tipik yapilandirma: YOLOv5-s 640 / 1000 epok, Ultralytics; "
                     "SURUM KARSILASTIRMASI IZGARASININ KENDI ardisik duzeni. conf 0,001 / IoU 0,5.",
            "n": len(_v), "ort": round(st.mean(_v),4), "ss": round(st.stdev(_v),4),
            "medyan": round(st.median(_v),4), "min": round(min(_v),4), "maks": round(max(_v),4),
            "sinif": {"malign_ort": round(st.mean(_vm),4), "malign_ss": round(st.stdev(_vm),4),
                      "benign_ort": round(st.mean(_vb),4), "benign_ss": round(st.stdev(_vb),4)},
            "kaynak": "veri/seed30_yolov5s_surumkohortu_20260730.csv",
            "not_": "KOHORT A ILE KARISTIRILMAZ. Kohort A = YOLOv5-s 448, transformer catali "
                    "(COCO on-egitimli, lr0 0,001, mixup 0,243, 6000 epok), ss 4,38. Aile "
                    "ortalamalari izgaradan geldigi icin aile kiyasinin bandi KOHORT C'dir.",
        }
        K["_kaynaklar"]["kohort_C"] = {"yol": _yc, "md5": sha(_yc)}

# --- [2] HELDOUT ALT KUME (tavan etkisi) -------------------------------------
# Bulgu #9: taslak ortusmeyen alt kume icin 0,99 yaziyordu; olculen ortalama
# 0,9687, ortanca 0,9817 -- ve ayni cumledeki 98,2 ortancaya karsilik geliyor.
# Bulgu #10: bu sayilar "kanonik olmayan on deger" diye nitelenip yine de metne
# alinmisti; kayda alinarak celiski cozulur (kural bos beyanla degil kayitla kapanir).
_rh, _yh = _oku("_heldout_altkume_v3_910_20260910.csv")
if _rh:
    _H = {}
    for _ak in sorted(set(x.get("altkume","") for x in _rh)):
        _vv = [_f(x["all_mAP50"]) for x in _rh
               if x.get("altkume")==_ak and abs((_f(x.get("conf")) or -1)-0.001)<1e-9 and _f(x.get("all_mAP50")) is not None]
        if not _vv: continue
        _H[_ak] = {"n": len(_vv), "ort": round(st.mean(_vv),4), "ortanca": round(st.median(_vv),4),
                   "min": round(min(_vv),4), "maks": round(max(_vv),4),
                   "tavana_ulasan": sum(1 for z in _vv if z>=0.995),
                   "tavan_esigi": 0.995}
    K["heldout_altkume"] = {
        "tanim": "Tutulan alt kume denetimi: egitim/test ortusmesi olan ve olmayan hucreler ayri "
                 "olculdu. conf 0,001 / IoU 0,5. Tavan etkisi savinin kanit tabani.",
        "altkumeler": _H,
        "kaynak": "veri/_heldout_altkume_v3_910_20260910.csv (910 olcumu, 10.09.2026)",
        "not_": "ORTALAMA ile ORTANCA AYRI RAPORLANIR: ortusmeyen alt kumede ortalama 0,97, ortanca "
                "0,98; 0,99 degeri HICBIR istatistige karsilik gelmez (maks 0,995). Metinde hangi "
                "istatistik oldugu yazilmazsa ayni cumlede celiski uretir (bulgu #9).",
    }
    K["_kaynaklar"]["heldout_altkume"] = {"yol": _yh, "md5": sha(_yh)}

# --- [3] PARAMETRE SAYISI (nc=2, olculmus) -----------------------------------
# Bulgu #14 YANLIS POZITIF cikti: denetim ajani yayimli nc=80 degerlerini (2,6/9,1/
# 25,1M) kullanip "dort ve on iki kat" iddiasini ~3,5x ve ~9,7x diye duzeltmek
# istedi. Bu calisma nc=2 ile egitiyor; depo yaml'larindan nc=2 ile OLCULDUGUNDE
# oranlar 3,98x ve 11,82x, yani taslaktaki ifade DOGRU. Eksik olan sayi degil,
# OLCUM TEMELININ BEYANI. Ajanin onerisi uygulanirsa taslaga hata girerdi.
_rp, _yp = _oku("_parametre_nc2_155_20261017.csv")
if _rp:
    _P = {x["varyant"]: {"parametre": int(x["parametre"]), "yaml": x["yaml"],
                         "yaml_md5": x["yaml_md5"], "depo": x["depo"]} for x in _rp}
    _n = _P.get("yolov5n",{}).get("parametre")
    K["parametre_nc2"] = {
        "tanim": "YOLOv5 varyantlarinin parametre sayisi, BU CALISMANIN sinif sayisiyla (nc=2), "
                 "deponun kendi model tanimlarindan olculdu: models.yolo.Model(yaml, ch=3, nc=2).",
        "varyantlar": _P,
        "oranlar": ({k: round(v["parametre"]/_n,2) for k,v in _P.items()} if _n else None),
        "kaynak": "veri/_parametre_nc2_155_20261017.csv",
        "not_": "YAYIMLI DEGERLERLE KARISTIRILMAZ: Ultralytics model karti nc=80 icindir (2,6/9,1/"
                "25,1M -> 3,5x ve 9,7x). nc=2'de Detect basi kuculdugu icin oranlar 3,98x ve 11,82x "
                "olur; 'dort ve on iki kat' nitelemesi bu olcume dayanir. Tez parametre sayisini "
                "olcmedigini beyan ettigi icin (kanonik/bolum3.tex:139) sayi burada olculup kaydedildi.",
    }
    K["_kaynaklar"]["parametre_nc2"] = {"yol": _yp, "md5": sha(_yp)}

# --- [4] ESLI REJIM FARKI (map1 - 252550) ------------------------------------
# Bulgu #11: taslak -0,14 ve GA [-1,45; +1,18] yaziyordu; olculen +0,137 ve
# [-1,178; +1,451]. Isaret ve GA uclari ters. Ayni cumledeki ortalamalar
# (map1 83,43 > 252550 83,29) taslagin kendi isaretiyle celisiyordu.
_rb2, _yb2 = _oku("_bandA_BIRLESIK_conf0001_20260814.csv")
if _rb2:
    def _rej(rej, kon="kazanan"):
        return {x["seed"]: _f(x["all_mAP50"]) for x in _rb2
                if x.get("rejim")==rej and x.get("konfig")==kon and _f(x.get("all_mAP50")) is not None}
    _E = {}
    for _a,_b in (("map1","252550"), ("map1","333334"), ("252550","333334")):
        _d1,_d2 = _rej(_a), _rej(_b)
        _ks = sorted(set(_d1)&set(_d2))
        if len(_ks) < 3: continue
        _ff = [(_d1[k]-_d2[k])*100 for k in _ks]
        _m, _sd, _n2 = st.mean(_ff), st.stdev(_ff), len(_ff)
        _t = t_kritik(_n2-1) if "t_kritik" in dir() else 2.045
        _E["%s_eksi_%s" % (_a,_b)] = {
            "n": _n2, "fark_puan": round(_m,4),
            "ga95": [round(_m-_t*_sd/math.sqrt(_n2),4), round(_m+_t*_sd/math.sqrt(_n2),4)],
            "ort_%s" % _a: round(st.mean([_d1[k] for k in _ks])*100,4),
            "ort_%s" % _b: round(st.mean([_d2[k] for k in _ks])*100,4),
            "yon": "ilk terim yuksek" if _m>0 else "ikinci terim yuksek",
        }
    K["esli_rejim_farki"] = {
        "tanim": "Uygunluk rejimleri arasindaki TOHUM-ESLI fark (kazanan konfigurasyon, n=30). "
                 "Isaret 'birinci eksi ikinci' olarak tanimlidir.",
        "ciftler": _E, "kaynak": "veri/_bandA_BIRLESIK_conf0001_20260814.csv",
        "not_": "ISARET TANIMI ZORUNLU: fark yonunun metinde hangi terimden hangisine oldugu "
                "yazilmazisa ayni cumledeki ortalamalarla celisir (bulgu #11).",
    }

# --- [5] IKIZ EGITIM (iki bagimsiz egitim arasindaki fark) -------------------
# Bulgu #13: taslak medyan 2,1 icin "bandin ongordugu mertebededir" diyordu.
# Olculen: medyan 2,095 -> ima edilen sigma 2,20; bandin ongordugu medyan
# Kohort A icin 4,18 (sigma 4,38), Kohort C icin 4,77 (sigma 5,00). Yani
# olculen deger ongorulenin YARISI. Ikiz ciftler ayni makine/ayni derlemede
# kosuldugundan DAR bir yeniden-egitim bandi veriyor: band kaniti degil ALT SINIR.
_ri, _yi = _oku("_ikiz_egitim_155_20261017.csv")
if _ri:
    _dd = [_f(x["fark_puan"]) for x in _ri if _f(x.get("fark_puan")) is not None]
    _vr = sorted(set(x["model"] for x in _ri))
    _med = st.median(_dd)
    _ima = _med/(0.6745*math.sqrt(2))
    _K = {}
    for _s,_ad in ((4.38,"kohortA"),(5.00,"kohortC")):
        _bek = 0.6745*_s*math.sqrt(2)
        _K[_ad] = {"sigma": _s, "beklenen_medyan_puan": round(_bek,4), "olculen_bolu_beklenen": round(_med/_bek,4)}
    K["ikiz_egitim"] = {
        "tanim": "Ayni hucrenin iki bagimsiz egitimi arasindaki mAP@0,5 farki (conf 0,001 / IoU 0,5). "
                 "Iki kanonik izgara ihracinin ORTAK hucrelerinden, birebir ayni olanlar (369, ayni "
                 "kosumun yeniden ihraci) DISLANARAK elde edildi.",
        "n_konfig": len(_dd), "n_varyant": len(_vr),
        "min": round(min(_dd),4), "maks": round(max(_dd),4),
        "medyan": round(_med,4), "ort": round(st.mean(_dd),4),
        "ima_edilen_sigma": round(_ima,4),
        "band_karsilastirmasi": _K,
        "varyantlar": _vr,
        "kaynak": "veri/_ikiz_egitim_155_20261017.csv (kaynaklar: kanonik_kaynak/"
                  "BIRLESIK_v3_v12_grid_20260708.csv ve BIRLESIK_v3_v12_grid_SGDfinal_20260728.xlsx)",
        "not_": "BAND KANITI DEGIL ALT SINIR: ciftler ayni makinede ve ayni derlemede kosuldu, yani "
                "tohum + cozulmus parti disindaki oynaklik kaynaklari sabit. Olculen medyan bandin "
                "ongordugunun yarisi (0,50x Kohort A, 0,44x Kohort C); 'bandin ongordugu mertebede' "
                "nitelemesi bu nedenle fazladir (bulgu #13).",
    }
    K["_kaynaklar"]["ikiz_egitim"] = {"yol": _yi, "md5": sha(_yi)}


# --- [6] KOHORT B, IKI GUVEN ESIGINDE (esik = degerin kimligi, H92) -----------
# Mac-inceleme'nin esik acigi bulgusu: yeniden-uretilememe iddiasi conf 0,001'de
# kurulu, ama makalenin kendi tablosu conf 0,25'te maks 79,9 gosteriyor ve bu sayi
# sampiyonun conf 0,001'deki 79,90'ina yakin dusuyor. Iki esik ayri kalem olarak
# kaydedilir ki metinde eslesmemis bir kiyas kurulamasin.
# OLCUM: en yuksek kosumun KIMLIGI iki esikte de ayni (tohum 8); esigin degistirdigi
# sey siralama degil DUZEY. Mac'in "tohum 8 ikisinde de malign-agir" ek gozlemi
# OLCUMLE TUTMUYOR: conf 0,001'de malign sirasi 7/30, benign sirasi 4/30 -- her iki
# sinifta da kohort ortalamasinin UZERINDE, yani sinif-yanli degil. Yazilmadi.
_rk, _yk = _oku("seed30_yolov9c_20260728.csv")
if _rk:
    _E6 = {}
    for _cf in ("0.001", "0.25"):
        _vv = [(x["seed"], _f(x["mAP50"])*100, _f(x["mAP50m"])*100, _f(x["mAP50b"])*100)
               for x in _rk if (x.get("Conf") or "").strip()==_cf and _f(x.get("mAP50")) is not None]
        if not _vv: continue
        _g = sorted(_vv, key=lambda z: -z[1])
        _m = [z[0] for z in sorted(_vv, key=lambda z: -z[2])]
        _bn = [z[0] for z in sorted(_vv, key=lambda z: -z[3])]
        _en = _g[0]
        _E6[_cf] = {
            "n": len(_vv), "ort": round(st.mean([z[1] for z in _vv]),4),
            "ss": round(st.stdev([z[1] for z in _vv]),4), "maks": round(_en[1],4),
            "en_yuksek_tohum": _en[0],
            "en_yuksek_kosumun_siniflari": {
                "malign": round(_en[2],4), "malign_sirasi": _m.index(_en[0])+1,
                "benign": round(_en[3],4), "benign_sirasi": _bn.index(_en[0])+1},
            "kohort_sinif_ort": {"malign": round(st.mean([z[2] for z in _vv]),4),
                                 "benign": round(st.mean([z[3] for z in _vv]),4)},
        }
    # ikinci en yuksek kosum (conf 0,001): §3.3'teki zit-yonlu profil cifti
    _v1 = [(x["seed"], _f(x["mAP50"])*100, _f(x["mAP50m"])*100, _f(x["mAP50b"])*100)
           for x in _rk if (x.get("Conf") or "").strip()=="0.001" and _f(x.get("mAP50")) is not None]
    _s1 = sorted(_v1, key=lambda z: -z[1])[:2]
    K["kohortB_esikler"] = {
        "tanim": "Kohort B (YOLOv9-c, 30 tohum) iki guven esiginde ayri ayri. ESIK DEGERIN "
                 "KIMLIGIDIR: iki esikteki degerler karsilastirilamaz.",
        "esikler": _E6,
        "esik_kararliligi": {
            "en_yuksek_tohum_her_iki_esikte_ayni":
                (_E6.get("0.001",{}).get("en_yuksek_tohum") == _E6.get("0.25",{}).get("en_yuksek_tohum")),
            "yorum": "Esigin degistirdigi sey kosumlarin siralamasi degil degerlerin duzeyidir.",
        },
        "zit_yonlu_cift_conf0001": [
            {"tohum": z[0], "genel": round(z[1],4), "malign": round(z[2],4), "benign": round(z[3],4)}
            for z in _s1],
        "kaynak": "veri/seed30_yolov9c_20260728.csv",
        "not_": "SAMPIYONUN conf 0,25 KARSILIGI OLCULMEMISTIR; conf 0,25'teki kohort maksimumu "
                "(79,9) ile sampiyonun conf 0,001 degeri (79,90) arasinda kurulacak eslesme "
                "GECERSIZDIR. Sayisal yakinlik rastlantidir.",
    }


# --- DEGERLENDIRME HATTI: cerceveye DORDUNCU boyut -- degerlendirme PARTI boyutu ---
# Mac-inceleme [4] uzerine kopru dosyasinin protokolunu ararken cikti: 0,19 puanlik
# "degerlendirme hatti yeniden uretilemezligi" (sinirlilik xiii) belirsiz bir
# "AP toplanma adimi" degil, DEGERLENDIRME PARTI BOYUTUNUN etkisi. Ayni agirlik:
#   parti 1  -> 0,799009 · parti 16 -> 0,800396 · kanonik EK6 -> 0,800953
# P ve R alti haneye kadar ortustugu icin fark AP integrasyonunda, ve onu kaydiran
# degisken parti. Yani cerceve = {esik, IoU, sinif, epok, birim, nc, PARTI}.
# Kaynak cagdas kayit: PLAN_makale_20261003.md:2907 (olcum aninda yazildi).
K["degerlendirme_hatti"] = {
    "tanim": "Ayni agirlik dosyasinin ayni esikte (conf 0,001 / IoU 0,5) iki ayri "
             "degerlendirme gecisinde verdigi degerler.",
    # --- OLCULEN (ham dosyalardan okundu; hicbiri cikarim degil) ---
    "olculen": {
        "kanonik_ek6": {"mAP50": 0.8009532468, "P": 0.9280985849, "R": 0.6974789916,
                        "AP_malign": 0.8910428571, "AP_benign": 0.7108636364,
                        "kaynak": "kanonik/_910_EK6_504_sinif_bazli_20260910.csv (YOLOv9-c 640/1000)",
                        "parti": "BILINMIYOR -- bu bir KAYIT ADI, parti ayari degil"},
        "yeniden_olcum_parti1": {"mAP50": 0.799009, "P": 0.928098, "R": 0.697479,
                        "AP_malign": 0.891043, "AP_benign": 0.706975,
                        "kaynak": "veri/_sampiyon_seed00_yeniden_degerlendirme_155_20261013.csv",
                        "parti": 1, "donanim": "155, CPU"},
        "yeniden_olcum_parti16": {"mAP50": 0.800396, "P": None, "R": None,
                        "AP_malign": None, "AP_benign": None,
                        "kaynak": "PLAN_makale_20261003.md:2908 (cagdas kayit)",
                        "parti": 16,
                        "not_": "P/R ve sinif degerleri KAYITTA YOK; yalniz genel mAP var"},
    },
    "yayilim_puan": round((0.8009532468 - 0.799009) * 100, 4),
    # --- OLCULEN AYRISTIRMA: farkin nerede oldugu, cikarimla degil hesapla ---
    "ayrisma_yeri": {
        "P_fark": round(abs(0.9280985849 - 0.928098), 8),
        "R_fark": round(abs(0.6974789916 - 0.697479), 8),
        # [D1] Mac-inceleme: sert 0.0 bir OLCUM degil, yuvarlama-sinirli UST SINIR.
        # parti1 degeri alti haneye yuvarlak oldugundan fark ~5e-5 puanin altinda
        # OLCULEMEZ. Komsu alanlar (P_fark, R_fark) sifir-disi yazilmisti; bu alan
        # fazla soyluyordu. Hesaplanan deger de yaziliyor.
        "AP_malign_fark_hesaplanan_puan": round((0.8910428571 - 0.891043) * 100, 8),
        "AP_malign_fark_ust_siniri_puan": 5e-05,
        "AP_malign_fark_olculebilirlik": ("OLCULEMEZ: parti1 alti haneye yuvarlak; "
                                          "gercek fark 5e-05 puanin altinda olabilir"),
        "AP_benign_fark_puan": round(abs(0.7108636364 - 0.706975) * 100, 4),
        "kimlik": "genel = (AP_malign + AP_benign)/2",
        "kimlik_denetimi": round(abs(((0.8910428571 + 0.7108636364) / 2
                                      - (0.891043 + 0.706975) / 2) * 100
                                     - (0.8009532468 - 0.799009) * 100), 6),
        "hukum": ("P, R ve AP_malign ALTI HANEDE BIREBIR; butun fark TEK SINIFIN "
                  "(7 ornekli benign) AP degerinde (0,3889 puan), iki sinifli ortalamada "
                  "yarilanarak 0,1944 puan veriyor."),
    },
    # --- CIKARIM (olcum DEGIL; H87 geregi ayri alanda ve gerekceli) ---
    "cikarim": {
        "sav": ("P ve R birebir ortustugune gore TESPITLER OZDES; ozdes tespitlerden "
                "farkli AP cikmasi, ancak AP'nin TOPLANMA DISIPLININDEN olabilir "
                "(kurede havuzlanip bir kez integre edilmesi mi, parti basina "
                "ortalanmasi mi). Dolayisiyla PARTI BOYUTU NEDENSEL DEGISKEN DEGIL, "
                "toplanma disiplinini GORUNUR KILAN belirtidir."),
        "kaynak": "Mac-inceleme itirazi 18.10.2026; 155 P/R esitligini olcerek dogruladi",
        "onceki_yanlis_ifadem": ("'0,19 puan degerlendirme parti boyutunun etkisidir' "
                                 "demistim; parti belirti, neden degil. Duzeltildi."),
        "durum": "CIKARIM -- olculmedi",
        "yanlislanabilir_ongoru": {
            "1": "Kurede havuzlanmis hesap BIREBIR 0,800953 vermeli (yaklasik degil).",
            "2": "Parti 2/4/8 degerleri 0,799009 ile 0,800953 arasina TEKDUZE dusmeli.",
            "gozlenen_uyum": "parti_1 < parti_16 < EK6 siralamasi ongoruyle uyumlu",
            "sinama_maliyeti": "tek degerlendirme gecisi; EGITIM GEREKMEZ",
            "engel": ("sampiyon agirligi dnnlab3'un SSD'sinde (/media/.../dnnlab3/...), "
                      "155'te yerel kopya YOK -> sinama dnnlab3'te kosulmali"),
        },
    },
    "duzey_uyarisi": ("UC DUZEYDEN BIRININ DUZEY-DEGERI BILINMIYOR: 'kanonik_ek6' bir "
                      "KAYIT ADI, bir parti ayari degil. Bu haliyle parti en iyi halde "
                      "SIRALI bir degisken; nicel bir parti-etkisi egrisi kurulamaz. "
                      "Ayrica duzey basina n=1."),
    "cerceve_dersi": ("Cerceve, esik ve IoU ile bitmiyor: ayni baytlar ayni esikte iki "
                      "degerlendirme gecisinde farkli sayi veriyor. Bildirilmesi gereken "
                      "sey PARTI BOYUTU degil, AP TOPLANMA DISIPLINIDIR; parti onu "
                      "gorunur kilar."),
    "kaynak": ("kanonik/_910_EK6_504_sinif_bazli_20260910.csv + "
               "veri/_sampiyon_seed00_yeniden_degerlendirme_155_20261013.csv + "
               "PLAN_makale_20261003.md:2907-2908 (parti-16 icin cagdas kayit)"),
}

# --- OLUMSUZ SONUC: P/R uzerinden esik cikarimi AYIRT EDICI DEGIL (olculdu) ----
# Mac-inceleme [3] denedi ve ben dogruladim. Kayda giriyor ki ileride ayni yol
# yeniden denenmesin: olumsuz sonuc da sonuctur.
_rn, _yn = _oku("seed30_yolov9c_20260728.csv")
if _rn:
    def _kol(cf, k):
        return [float(x[k]) for x in _rn if (x.get("Conf") or "").strip() == cf and x.get(k)]
    _p1, _p2 = _kol("0.001", "Pm"), _kol("0.25", "Pm")
    _r1, _r2 = _kol("0.001", "Rm"), _kol("0.25", "Rm")
    if _p1 and _p2:
        K["olumsuz_sonuc_esik_cikarimi"] = {
            "soru": "Kaydedilmis P/R degerlerinden, kaydi olmayan bir olcumun guven esigi "
                    "geriye dogru cikarilabilir mi?",
            "yontem": "Ayni kohortun iki esikteki Pm/Rm dagilimlari karsilastirildi (n=30+30).",
            "conf_0001": {"Pm_ort": round(st.mean(_p1), 4), "Pm_aralik": [round(min(_p1), 3), round(max(_p1), 3)],
                          "Rm_ort": round(st.mean(_r1), 4)},
            "conf_025": {"Pm_ort": round(st.mean(_p2), 4), "Pm_aralik": [round(min(_p2), 3), round(max(_p2), 3)],
                         "Rm_ort": round(st.mean(_r2), 4)},
            "yon": "beklendigi gibi: esik artinca P yukari, R asagi",
            "buyukluk": round(st.mean(_p2) - st.mean(_p1), 4),
            "araliklar_ortusuyor": not (max(_p1) < min(_p2) or max(_p2) < min(_p1)),
            "hukum": "AYIRT ETMIYOR",
            "ikinci_gerekce": ("Ustelik kiyas kendi ilkemize takiliyor (H93): kopru dosyasinin "
                               "P'si GENEL, kohortun Pm'si SINIF BAZLI -- iki buyukluk ayni "
                               "cercevede degil."),
            "sonuc": ("P/R rejimi uzerinden esik cikarimi bu veri kumesinde kullanilamaz; "
                      "cerceve ya kayitta olur ya da satir kimligiyle/cagdas kayitla kurulur."),
            "kaynak": "veri/seed30_yolov9c_20260728.csv (Mac-inceleme onerdi, 155 dogruladi)",
        }

# --- SEKIZINCI BOYUT: ORTALAMA DISIPLINI (makro vs mikro) -- OLCULDU ----------
# Mac-inceleme buldu ve 504 hucrede sinadi; 155 bagimsiz dogruladi. Yedinci boyut
# (degerlendirme partisi) 0,19 puandi; bu onun 27 KATI: 5,25 puan.
# Kayitta "makro"/"mikro" sozcukleri SIFIR kez geciyordu.
_re6, _ye6 = None, None
for _ad6, _kk6 in list(K["_kaynaklar"].items()):
    if _ad6 == "ek6_sinif_csv": _ye6 = _kk6.get("yol")
if _ye6 and os.path.exists(_ye6):
    with open(_ye6, newline="", encoding="utf-8", errors="replace") as _f6:
        _re6 = list(csv.DictReader(_f6))
if _re6:
    def _ff(x):
        try: return float(x)
        except Exception: return None
    _mk_r = _mk_m = _mi_r = _gec = 0
    for _x6 in _re6:
        _ra, _rm, _rb = _ff(_x6.get("R_all")), _ff(_x6.get("R_malign")), _ff(_x6.get("R_benign"))
        _ma, _mm, _mb = _ff(_x6.get("mAP50_all")), _ff(_x6.get("mAP50_malign")), _ff(_x6.get("mAP50_benign"))
        if None in (_ra, _rm, _rb, _ma, _mm, _mb): continue
        _gec += 1
        if abs(_ra - (_rm + _rb) / 2) < 1e-6: _mk_r += 1
        if abs(_ma - (_mm + _mb) / 2) < 1e-6: _mk_m += 1
        if abs(_ra - (17 * _rm + 7 * _rb) / 24) < 1e-6: _mi_r += 1
    _c6 = [_x6 for _x6 in _re6 if _ff(_x6.get("mAP50_all")) and abs(_ff(_x6["mAP50_all"]) - 0.800953) < 1e-6]
    _sf = None
    if _c6:
        _rm0, _rb0 = _ff(_c6[0]["R_malign"]), _ff(_c6[0]["R_benign"])
        _sf = {"R_malign": round(_rm0, 6), "R_benign": round(_rb0, 6),
               "makro_R": round((_rm0 + _rb0) / 2, 6),
               "mikro_R": round((17 * _rm0 + 7 * _rb0) / 24, 6),
               "fark_puan": round(abs((_rm0 + _rb0) / 2 - (17 * _rm0 + 7 * _rb0) / 24) * 100, 4),
               "mikro_kesri": "18/24 (14 malign + 4 benign dogru pozitif)"}
    # Alanyazin bildirim orani: OLCULMEDI (Mac-inceleme [2]). Derlemenin sessizligi
# kaynaklarin sessizligi sayilamaz -- M5'in cikarimi bu alani hic tasimiyor, dolayisiyla
# "43 calismanin kaci bildiriyor" sorusuna veri YOK. Oranı olmayan bir iddia metne
# girmemeli; girdigi iki yer bulunup duzeltildi.
K["alanyazin_bildirim_orani"] = {
    "soru": "Alanyazinda sinif ustu ozetin ortalama disiplini hangi siklikta bildiriliyor?",
    "durum": "OLCULMEDI",
    "gerekce": ("M5 derlemesinin cikarim semasi (tab:ozet43) bildirilen metrik DEGERLERINI "
                "ve etiketlerini tasiyor; ortalama disiplinini tasimiyor. Derlemenin "
                "duzyazisinda da ortalama anlaminda makro/mikro gecmiyor."),
    "neden_orana_cevrilemez": ("Derlemenin NE KAYDETTIGI ile kaynaklarin NE BILDIRDIGI ayri "
                               "seylerdir. Birinciden ikincisini cikarsamak, ozetten kaynagi "
                               "cikarsamaktir (H87 ailesi). Dolayisiyla dogru ifade "
                               "'bildirilmiyor' degil 'OLCULMEDI'dir."),
    "metinde_duzeltilen": ("Taslaga iki olculmemis siklik iddiasi yazmisim ve ikisi de son iki "
                           "turda eklenmisti: §2.3 'alanyazinda ... siklikla belirtilmez' ve "
                           "(xiii) 'toplanma disiplini alanyazinda nadiren bildirilir'. Ikisi "
                           "de 'bu calismada OLCULMEMISTIR' beyanina cevrildi."),
    "olculmeye_deger_asil_soru": ("Cok sinifli ve sinif dengesizligi olan calismalarin kaci "
                                  "YALNIZ toplulastirilmis degeri bildiriyor? (Mac-inceleme [4])"),
    "geri_alinan_genelleme": {
        "iddia": ("Mac-inceleme ilk olarak 'Ultralytics/COCO ekosisteminde mAP YAPI GEREGI "
                  "makrodur; disiplini ARAC belirler, yazar secmez' demisti; 155 bu genellemeye "
                  "dayanarak §2.3'e 'kullanilan catilarda disiplin aracin kendisi tarafindan "
                  "belirlenir' yazdi."),
        "durum": "GERI ALINDI -- Mac kendi genellemesini olcerek sinirladi (18.10)",
        "karsi_ornek": {
            "kaynak_calisma": "10.1016/j.cmpb.2020.105823 (Aly), IOU=0,5",
            "raporlanan": {"AP_benign": 33.0, "AP_malign": 52.00, "mAP": 42.21},
            "makro_beklenen": 42.5,
            "fark_puan": 0.29,
            "yuvarlama_kurtariyor_mu": ("HAYIR: makro icin AP toplami 84,42 olmaliydi, "
                                        "yazili toplam 85,00"),
            "agirlikli_cozum": {"w_benign": 0.515263, "kontrol": 42.21,
                                "ima_edilen_oran_nm_nb": 0.9408},
            "hukum": "bu SATIR makro ile tutmuyor; agirlikli ortalama ile birebir tutuyor",
        "UCUNCU_KATMAN_18_10": {
            "windows_olcumu": ("Windows ASIL TABLOYU okudu: 27 satirin 21'i MAKRO. Agirlikli "
                               "hipotez isaret sinamasiyla CURUK -- bir satir w>0,5, oteki "
                               "w<0,5 gerektiriyor, sabit agirlik IMKANSIZ. Alti satir "
                               "makroyla tutmuyor ve yuvarlama bunu ortmuyor (Windows'un "
                               "sinirlari 0,0325-0,055, gozlenen 0,10); yani sapanlar "
                               "NEDENSIZ, 'agirlikli' degil."),
            "sonuc": ("Mac'in tek satirdan cikardigi 'o calisma agirlikli kullaniyor' hukmu "
                      "CURUDU. Dolayisiyla bu karsi ornek, BASKA CALISMALARIN farkli disiplin "
                      "kullandigini KURMUYOR; yalniz alti satirin aciklanmamis kaldigini "
                      "gosteriyor."),
            "§2.3_ETKILENMEDI_NEDEN": ("Daraltma bastan ALY'YE DAYANMADI, kendi olcumumun "
                                       "KAPSAMINA dayandi: '504/504 dogrulama bu calismanin "
                                       "ardisik duzeniyle sinirlidir'. Bir kapsam beyani, "
                                       "baskalarinin ne yaptigina dair hicbir iddia tasimaz. "
                                       "Karsi ornek curuse de, cuurumese de metin ayni kalir. "
                                       "Hukmu olculene baglamanin bedeli yoktu, getirisi bu."),
            "ders": ("UC KATMANLI ZINCIR: (1) Mac genelleme yapti, (2) Mac kendi genellemesini "
                     "tek satirlik bir olcumle geri aldi, (3) Windows o tek satirlik olcumun "
                     "HUKMUNU asil tablodan curuttu. Her katmanda sav daraldi. Metin hicbirinden "
                     "etkilenmedi cunku hicbirine dayanmamisti."),
        },
            "CEKINCE": ("Hesap windows'un ALINTISINDAN yapildi, makalenin ASIL TABLOSUNDAN "
                        "DOGRULANMADI; alinti kismi olabilir. Bu cekince DOGRU CIKTI: Windows "
                        "tabloyu okudugunda 21/27 makro buldu. DERS CEKINCEDE, YARGIDA DEGIL "
                        "(Mac'in kendi duzeltmesi): Mac yanlis sonuca vardi; cekince o "
                        "sonucun BEDELINI ucuzlatti ve hatayi BIR ILETIDE kapatti. "
                        "Dogrulanan sey Mac'in hukmu degil, KAPSAM CEKINCESININ ISLEVI. "
                        "Ne makro kaniti ne karsi kanit olarak KULLANILMAZ; metinde "
                        "KULLANILMADI."),
        },
        "metne_etkisi": ("§2.3 daraltildi ve daraltma BU CALISMANIN KENDI OLCUMUNE dayaniyor, "
                         "Aly'ye degil: 'bu dogrulama bu calismanin ardisik duzeniyle sinirlidir; "
                         "farkli bir ardisik duzende ya da kendi degerlendirme kodunu yazan bir "
                         "calismada disiplin degisebilir'. Boylece hukum olculenle sinirli kalir "
                         "ve disarisi icin siklik ima etmez."),
    },
    "ucuza_olculebilir_kilma": ("M5-R cikarim protokolune uc alan, 134 tam metin OKUNMADAN once: "
                                "ortalama_disiplini {makro,mikro,agirlikli,belirtilmemis} · "
                                "sinif_bazli_bildirim {var,yok,tek_sinif} · sinif_sayisi. Ucu de "
                                "BILDIRILEN DEGERIN YAKIN BAGLAMINDAN okunmali. Sonra eklenirse "
                                "ikinci bir tam metin turu demek. M5-R windows'un dosyasi (H85); "
                                "Mac windows'a iletti, 155 uygulamadi."),
    "m5_ile_iliski": ("M5'in oneri kumesi (iv) 'sinif bazli sonuclarin genel ortalamayla "
                      "birlikte verilmesi' diyor; M3 ayni eksenin FIYATINI olcuyor (5,2521 "
                      "puan). Recete + olculmus fiyat etiketi, bir orandan guclu bir katki: "
                      "'kac calisma yapiyor' degil 'yapmazsan su kadar kaybediyorsun'."),
}

K["ortalama_disiplini"] = {
        "tanim": "Sinif ustu ozetlerin MAKRO mu MIKRO mu alindigi. Makro: siniflarin "
                 "duz ortalamasi. Mikro: ornek sayilariyla agirlikli.",
        "deger": "MAKRO (sinif duz ortalamasi)",
        # OLCUTE GORE AYRILDI (Mac-inceleme 18.10): mikro/makro karsitligi her olcutte
        # tanimli DEGIL. R ornek basina ortalanabilir -> mikro TANIMLI. AP bir PR egrisi
        # integralidir -> ornek basina ortalanamaz; sinif AP'lerini sinif boyutuyla
        # agirliklandirmak STANDART HICBIR OLCUT uretmez. AP'de makronun gercek
        # alternatifi tespitlerin HAVUZLANMASIDIR ve o sinif AP'lerinden TURETILEMEZ.
        "dogrulama": {
            "makro_R": {"kimlik": "R_all = (R_m + R_b)/2", "sonuc": "%d/%d" % (_mk_r, _gec),
                        "tanimli_mi": True},
            "makro_mAP": {"kimlik": "mAP50_all = (mAP50_m + mAP50_b)/2",
                          "sonuc": "%d/%d" % (_mk_m, _gec), "tanimli_mi": True},
            "mikro_R": {"kimlik": "R_all = (17*R_m + 7*R_b)/24",
                        "sonuc": "%d/%d" % (_mi_r, _gec), "tanimli_mi": True,
                        "not_": "ELEME sinamasi: kayit mikro degil, makro"},
            "mikro_mAP": {"sonuc": "SINANMADI", "tanimli_mi": False,
                          "neden": ("AP bir PR egrisi integralidir, ornek basina ortalanamaz. "
                                    "'mikro mAP' diye standart bir buyukluk YOKTUR; sinif "
                                    "AP'lerini agirliklandirmak bir olcut uretmez. "
                                    "UYDURULMAMALIDIR.")},
        },
        "sampiyonda_fark": _sf,
        "OLCUT_ADI_ZORUNLU": ("5,2521 puan GERI CAGIRMA (R) eksenindendir. mAP sinif "
                              "AP'lerinden gelen sayi AP_tarafi.aralik_puan'dir ve o BIR STANDART OLCUT "
                              "DEGILDIR (agirlikli birlesim). Iki sayi ayni kipte yazilamaz; "
                              "sayinin yaninda OLCUT ADI durmali. Mac-inceleme bu sayiyi uc "
                              "iletide niteleyici olmadan tasidi; taslak 'duyarliligi' dedigi "
                              "icin dogru kalmisti, ama IKINCI gecis olcut adi tasimiyordu -> "
                              "eklendi (H93: degerin kimligi hangi olcutten geldigini icerir)."),
        # ARA SONUCLAR YUVARLANMAZ (Mac-inceleme 18.10): ilk yazimda makro degeri icin
        # YUVARLANMIS 0,800953'u kullandim; tam deger (AP_m+AP_b)/2 = 0,80095324675.
        # Fark son haneyi bozdu: 3,7538 yerine dogru deger 3,7537. Yuvarlama YALNIZ
        # sunum aninda. (Kardes vaka: parti1'in alti haneye yuvarlanmasi
        # AP_malign_fark_puan'i sert sifir gostermisti.)
        "AP_tarafi": {
            "makro_AP_sampiyon": round((0.8910428571 + 0.7108636364) / 2, 10),
            "agirlikli_makro_AP_sampiyon": round((17 * 0.8910428571 + 7 * 0.7108636364) / 24, 10),
            "aralik_puan": round(((17 * 0.8910428571 + 7 * 0.7108636364) / 24
                                  - (0.8910428571 + 0.7108636364) / 2) * 100, 4),
            "aralik_tam_puan": ((17 * 0.8910428571 + 7 * 0.7108636364) / 24
                                - (0.8910428571 + 0.7108636364) / 2) * 100,
            "ozdeslik": "aralik = (17/24 - 1/2) x (AP_malign - AP_benign)",
            "ara_yuvarlama_notu": ("Bu alan bir kez YANLIS hesaplandi: makro icin yuvarlanmis "
                                   "0,800953 kullanilmis, sonuc 3,7538 cikmisti. Tam girdilerle "
                                   "3,7537. Ara yuvarlama son haneyi bozar."),
            "UYARI": ("Yukaridaki aralik_puan bir OLCUT ARALIGI DEGIL: AGIRLIKLI MAKRO standart bir "
                      "buyukluk olmadigi icin kiyas noktasi da yoktur. Kayda yalniz 'mikro mAP "
                      "uydurulmamali' gerekcesini belgelemek icin girdi; METINDE KULLANILMAZ."),
            "ADLANDIRMA_DUZELTMESI": ("Windows (18.10): sinif AP'lerinin ornek sayisiyla "
                                      "agirlikli ortalamasi 'MIKRO' DEGIL, AGIRLIKLI MAKRO'dur. "
                                      "Mikronun gercek karsiligi butun tespitlerin TEK PR "
                                      "egrisinde havuzlanmasidir ve o sinif AP'lerinden "
                                      "TURETILEMEZ. Alan adi duzeltildi."),
            "SIFIRINCI_BASAMAK": ("Windows'un genellemesi: OLCUTUN TANIMI, DEGERLERIN "
                                  "ARITMETIGINDEN ONCE GELIR. Butun gun 'hangi sayi hangi "
                                  "kuralla kurulmus' diye sorduk; bir basamak geride "
                                  "'bu olcut icin o kural TANIMLI MI' sorusu duruyor. "
                                  "Anlamsiz bir olcumun nufusunu, birimini ve kuralini dogru "
                                  "secmek onu anlamli kilmaz. Somut sonucu: Aly'nin "
                                  "'agirlikli disiplin kullandigi' hipotezi UCUNCU ve en temel "
                                  "biciminde curudu -- havuzlanmis tespit B AP ile M AP'den "
                                  "HICBIR BICIMDE kurulamaz, yani VAR OLMAYAN bir alternatif "
                                  "sinaniyordu."),
            "gercek_alternatif": ("tespitlerin HAVUZLANIP tek AP hesaplanmasi; sinif AP'lerinden "
                                  "turetilemez, bu calismada OLCULMEDI -- degerlendirme_hatti."
                                  "cikarim'daki havuzlama ongorusuyle AYNI SORU."),
        },
        "neden_onemli": ("Sinif dengesizligi 17/7 oldugundan makro-mikro ayrimi buyuk: "
                         "sampiyonda duyarlilik makro ile 0,697479, mikro ile tam 0,750000 "
                         "-- 5,25 puan. Yedinci boyut (degerlendirme partisi) 0,19 puandi; "
                         "bu onun yirmi yedi kati."),
        "kaynak": "kanonik/_910_EK6_504_sinif_bazli_20260910.csv",
        "cerceve_kaniti": "kolon_ayirt_edici (veriden turetildi: 504/504 hucrede kimlik tutuyor)",
        "bulan": "Mac-inceleme 18.10.2026; 155 bagimsiz dogruladi (504/504 ve 0/504)",
    }

# --- VERI KUMESI SINIF SAYILARI: etiket dosyalarindan OLCULDU -----------------
# Mac-inceleme [C3]: taslaktaki "7 ornekli benign" ve "24 kitlelik test kumesi"
# kayitta KAYNAKSIZDI; Mac kaynaklandiramadi, yalniz celismedigini gosterebildi.
# Etiket dosyalarindan dogrudan sayildi -- Katman 0 kapaniyor.
_DS = os.path.expanduser("~/Desktop/damla_makale/dataset")
if os.path.isdir(_DS):
    _vk = {}
    for _bol in ("train", "test"):
        _fl = sorted(glob.glob(os.path.join(_DS, _bol, "labels", "*.txt"))) if "glob" in dir() else []
        if not _fl:
            import glob as _g
            _fl = sorted(_g.glob(os.path.join(_DS, _bol, "labels", "*.txt")))
        _sy = {"0": 0, "1": 0}
        for _fp in _fl:
            try:
                for _ln in open(_fp):
                    _ln = _ln.strip()
                    if _ln: _sy[_ln.split()[0]] = _sy.get(_ln.split()[0], 0) + 1
            except Exception:
                pass
        _vk[_bol] = {"goruntu": len(_fl), "kutu": sum(_sy.values()),
                     "malign": _sy.get("0", 0), "benign": _sy.get("1", 0)}
    if _vk.get("test", {}).get("kutu"):
        K["veri_kumesi"] = {
            "tanim": "INbreast kitle alt kumesi, bu calismanin sabit bolunmesi. Sinif "
                     "sayilari YOLO etiket dosyalarindan dogrudan sayildi.",
            "bolunmeler": _vk,
            "sinif_adlari": {"0": "malign", "1": "benign"},
            "kaynak": "damla_makale/dataset/{train,test}/labels/*.txt (data_4_1.yaml)",
            "not_": ("val: train ile AYNI dizin (data_4_1.yaml) -- secim korlugunun "
                     "mekanizmasi burada gorunuyor."),
            "kapatilan": ("taslaktaki '24 kitlelik test kumesi', '21 test goruntusu' ve "
                          "'7 ornekli benign sinif' ifadeleri artik kaynakli."),
        }

# --- IZGARA BLOGU: MAKINE KARISMASI (Mac-inceleme bulgusu + 155 karisma denetimi) ---
# Geri gelen uc blok kayda girdi ama CERCEVE DENETIMINDEN GECMEDI. Mac uc kalem bildirdi;
# ikisi dogrulandi, UCUNCUSU KENDI OLCUTUYLE CURUDU.
_ri2, _yi2 = None, None
for _a9, _k9 in list(K["_kaynaklar"].items()):
    if _a9 == "izgara_ham": _yi2 = _k9.get("yerel_yol", {}).get("yol") or _k9.get("yol")
if _yi2 and os.path.exists(_yi2):
    with open(_yi2, newline="", encoding="utf-8", errors="replace") as _f9:
        _ri2 = [x for x in csv.DictReader(_f9)
                if (x.get("conf") or "") == str(IZGARA_CONF) and (x.get("iou") or "") == str(IZGARA_IOU)]
if _ri2:
    _mm = _col.defaultdict(set)
    for _x9 in _ri2: _mm[_x9["model"]].add(_x9["machine"])
    _cok = [_m9 for _m9, _v9 in _mm.items() if len(_v9) > 1]
    _grup = {}
    for _g9 in sorted(set(_x9["group"] for _x9 in _ri2)):
        _sub = [_x9 for _x9 in _ri2 if _x9["group"] == _g9]
        _bil = _col.Counter(_x9["machine"] for _x9 in _sub)
        _ort = {_m9: st.mean([float(_x9["all_mAP50"]) for _x9 in _sub if _x9["machine"] == _m9]) * 100
                for _m9 in _bil}
        _tr = {}
        for _m9 in _bil:
            _dd = []
            for _x9 in _sub:
                if _x9["machine"] != _m9: continue
                _mt = re.search(r"backbone_([a-z-]+)_head_([a-z-]+)", _x9["model"])
                _dd.append(_mt.group(1).count("tr") if _mt else -1)
            _tr[_m9] = round(st.mean(_dd), 2)
        _grup[_g9] = {
            "n": len(_sub), "makine_bilesimi": dict(_bil),
            "makine_ortalamalari": {_m9: round(_v9, 2) for _m9, _v9 in sorted(_ort.items())},
            "havuz_ort": round(st.mean([float(_x9["all_mAP50"]) for _x9 in _sub]) * 100, 2),
            "makine_dengeli_ort": round(st.mean(list(_ort.values())), 2),
            "makine_araligi_puan": round(max(_ort.values()) - min(_ort.values()), 2),
            "makine_basina_omurga_tr_sayisi_ort": _tr,
        }
    K["_izgara_makine_karismasi"] = {
        "soru": "izgara_ozet'in uc grup ortalamasi karsilastirilabilir mi?",
        "gruplar": _grup,
        # --- DOGRULANAN (Mac [1]) ---
        "siralama_tersiniyor": {
            "havuz": {_g9: _v9["havuz_ort"] for _g9, _v9 in _grup.items()},
            "dengeli": {_g9: _v9["makine_dengeli_ort"] for _g9, _v9 in _grup.items()},
            "hukum": ("Gruplar DORT MAKINEDEN havuzlanmis ve makine bilesimleri AYNI DEGIL "
                      "(910'un payi 5 ile 121 arasinda degisiyor). Havuz siralamasiyla "
                      "makine-dengeli siralama 25-25-50 ve 33-33-34 arasinda TERSINIYOR. "
                      "Ustelik havuzda o ikisinin farki 0,04 puan -- bu calismanin kendi "
                      "onemlilik tabaninin (0,19 puan) besde biri. Uc grup ortalamasindan "
                      "siralama OKUNAMAZ."),
        },
        # --- KARISMA DENETIMI: Mac'in [3] 'armagani' BURADA CURUYOR ---
        "karisma_denetimi": {
            "birden_fazla_makinede_kosan_yapilandirma": len(_cok),
            "toplam_yapilandirma": len(_mm),
            "hukum": ("768 yapilandirmanin TAMAMI TEK makinede kosmus; ORTUSME SIFIR. "
                      "Dolayisiyla makine etkisi YAPILANDIRMA ATAMASINDAN AYRISTIRILAMAZ."),
            "atama_rastgele_degil": ("Makine basina omurga transformer sayisi sistematik olarak "
                                     "farkli (bkz. makine_basina_omurga_tr_sayisi_ort): bir grupta "
                                     "910'un bes yapilandirmasinda omurgada HIC transformer yok. "
                                     "Yani makine ortalamalari mimari AILELERININ ortalamalari."),
            "CURUYEN_ONERI": ("Mac-inceleme bu bloktaki makine araligini (8,97 / 5,75 / 8,13 puan) "
                              "ozetin 9,68 puanlik makineler arasi acikligina BAGIMSIZ DESTEK "
                              "olarak onerdi. KULLANILMAZ: burada makine ile mimari ailesi "
                              "karismis ve mimari farki TAM OLARAK o deneyin OLCTUGU SEY. "
                              "Makine araligini makine etkisi saymak, OLCULEN DEGISKENI OLCUM "
                              "ARACINA KOYMAK olur -- ki bu, Mac'in iki ileti once windows'a "
                              "alti sinifli calisma icin soyledigi olcutun kendisi. Oneri "
                              "kendi olcutuyle curudu."),
            "capraz_makine_NEDEN_FARKLI": ("capraz_makine blogunda AYNI yapilandirma, AYNI tohum, "
                                           "bayt duzeyinde AYNI veri ikinci bir makinede kosuldu; "
                                           "orada makine TEK degisken. Burada ise her yapilandirma "
                                           "tek makinede, yani kiyas capraz DEGIL."),
            "ozet_9_68_DEGISMEDI": "n_yineleme 1 olarak kaliyor; metinde degisiklik YAPILMADI.",
        },
        # --- BELIRSIZLIK (Mac [2]) ---
        "ad_belirsizligi": {
            "dosya_adi": "C3TR_kanonik_768.csv",
            "imgsz_kolonu": sorted(set(x.get("imgsz") for x in _ri2)),
            "ayrik_yapilandirma": len(_mm),
            "hukum": ("Addaki 768 YAPILANDIRMA SAYISIDIR, imgsz degil; imgsz kolonun tamaminda "
                      "448. Ad yanlis degil, CIFT OKUNABILIR -- YOLO ekosisteminde dosya adindaki "
                      "ciplak sayi imgsz okunur. Latent bir celiski, beyan edilmis bir cift "
                      "anlamdan kotudur, bu nedenle burada beyan edilir."),
        },
        # UCUNCU AYAK (Mac-inceleme olctu, 155 dogruladi): mimari <-> mAP iliskisi de
        # guclu. Yani "makine araligi" dedigimiz sey, o makinelerin is yukundeki MIMARI
        # BILESIMININ araligi -- ve mimari etkisi makine araligindan DAHA BUYUK.
        # Armagan yalniz gecersiz degil, TERSINE CEVRILMIS.
        "mimari_gradyani": {
            "tanim": "Omurgadaki transformer blogu sayisi ile mAP@0,5 iliskisi. Karismayi "
                     "YARATAN sey bu; ve kendi basina bloğun EN SAGLAM bulgusu.",
            "pearson": -0.5612, "n": 768,
            "katmanlar": {"tr=0": {"n": 48, "ort": 83.51}, "tr=1": {"n": 192, "ort": 81.07},
                          "tr=2": {"n": 288, "ort": 76.88}, "tr=3": {"n": 192, "ort": 74.42},
                          "tr=4": {"n": 48, "ort": 69.29}},
            "uctan_uca_puan": 14.22, "tekduze_mi": True,
            "hukum": ("Bu gorevde omurgaya transformer koymak mAP'yi TEKDUZE dusuruyor; "
                      "uctan uca 14,22 puan. Bu bir cerceve artefakti DEGIL, deneyin GERCEK "
                      "sonucu. Mimari etkisi (14,22) makine araligindan (8,97) BUYUK -- yani "
                      "makine araligi kismen mimari etkisini olcuyor."),
            "M3_ICIN": ("M3 yeniden uretilebilirlik uzerine; bu gradyan M3'e GIRMEZ. Kayda "
                        "giriyor cunku izgara blogu kayitta varken bloğun en saglam bulgusunu "
                        "disarida birakmak olurdu (Mac-inceleme onerisi)."),
            "kaynak": "veri/C3TR_kanonik_768.csv, conf 0,001 / iou 0,5 dilimi, n=768",
        },
        "KAPSAM_UYARISI": {
            "vaka": ("Omurga tr ortalamalari IKI KAPSAMDA olculdu ve sayilar ayristi; IKISI DE "
                     "DOGRU: grup ici (regime_25-25-50) 155: 1,57 · 475: 2,51 · 910: 0,00 · "
                     "994: 2,32 ↔ TUM DILIM (3 grup, n=768) 155: 1,47 (n=197) · 475: 2,49 "
                     "(n=343) · 910: 1,53 (n=177) · 994: 2,37 (n=51)."),
            "neden_onemli": ("'910: 0,00' okuyan biri 910'un HIC transformer kosmadigini sanir; "
                             "oysa 177 kosumda ortalama 1,53. Grup ici n=5 oldugu icin o bes "
                             "yapilandirmanin omurgasinda transformer yok, hepsi bu."),
            "kural": "Her katman ortalamasi KAPSAMIYLA yazilir (grup ici mi, tum dilim mi).",
        },
        "yeni_cerceve_boyutu": ("MAKINE. parti'nin birebir ayni bicimi: havuzlanan bir ozet, "
                                "katmanlarin agirliklari esit degilse katman kimligini tasimak "
                                "zorundadir. havuz - dengeli = (agirlik dengesizligi) x "
                                "(katman farki)."),
        "kaynak": "veri/C3TR_kanonik_768.csv (conf %s / iou %s dilimi)" % (IZGARA_CONF, IZGARA_IOU),
    }

# ============================================================================
# CERCEVE KUTUGU VE DEMIRI (17.10, Mac-inceleme'nin konsolidasyonu -- UST KURAL)
# "Bir degerin kimligi referans cercevesini icerir; iki deger, cerceveleri beyan
# edilip AYNI oldugu gosterilmeden karsilastirilamaz."
# H84 (mAP degiskesi) · H89 (md5 referans noktasi) · H92 (guven esigi) · H58
# (epok: en-iyi mi son mu) bu kuralin OZEL HALLERIDIR.
# Demir: her olcum blogu kutuge kayitli olmali, kutuk kaynak anahtarini
# _kaynaklar'da bulabilmeli, ve cercevenin NEREDEN geldigi beyan edilmeli --
# veride kolon olarak mi, dosya adindan mi, yoksa ardisik duzen beyanindan mi.
# Bu ucuncu alan H87 disiplininin cerceve tarafindaki karsiligidir: cerceveyi
# "biliyorum" demek ile "kayitta duruyor" demek ayri seylerdir.
# ============================================================================
_U = "uygulanmaz"
_CERCEVE = {
    "arklar":            dict(kaynak="band_csv", esik="conf 0,001", esik_kaynagi="dosya_adi",
                              iou="kayitta yok", birim="kosum", n=30),
    "esli":              dict(kaynak="band_csv", esik="conf 0,001", esik_kaynagi="dosya_adi",
                              iou="kayitta yok", birim="kosum (tohum-esli fark)", n=30),
    "rejim_etkisi":      dict(kaynak="band_csv", esik="conf 0,001", esik_kaynagi="dosya_adi",
                              iou="kayitta yok", birim="kosum", n=30),
    "tekil_zirve":       dict(kaynak="band_csv", esik="conf 0,001", esik_kaynagi="dosya_adi",
                              iou="kayitta yok", birim="kosum", karsilastirilan="tez tablosu degeri"),
    "secim_korlugu":     dict(kaynak="plato_csv+bvl_csv", esik="conf 0,001",
                              esik_kaynagi="beyan", iou="kayitta yok",
                              birim="hucre", epok="aile x epok ayrimi kalemde"),
    "sinif_bazli":       dict(kaynak="ek6_sinif_csv", esik="conf 0,001",
                              esik_kaynagi="beyan", iou="0,5 (ardisik duzen)",
                              birim="hucre", n=504),
    # CERCEVE GERI KAZANILAMIYOR: ureten betik depoda yok, val args.yaml korunmamis,
    # CSV'de kolon yok. "Beyan" bile degil -- hicbir kayitta durmuyor. Yeniden olcum
    # (cerceve kolonlariyla) tek care; dnnlab3 gerekir (ayni makine zorunlu).
    "ayristirma_kolu":   dict(kaynak="ayristirma30", esik="conf 0,001",
                              esik_kaynagi="yok", iou="kayitta yok",
                              birim="kosum", n=30, sinif="malign/benign ayri",
                              tasidigi="§3.3 varyans ayrisimi, sira ortusmesi, z=3,27"),
    "capraz_makine":     dict(kaynak="capraz_makine", esik="conf 0,001",
                              esik_kaynagi="yok", iou="kayitta yok",
                              birim="puan ve tensor sayisi", n=1,
                              tasidigi="ozdeki ve (xii)'deki 9,68 puanlik makineler arasi aciklik"),
    "cozulen_optimizer": dict(kaynak="cozulen_optimizer", esik=_U, esik_kaynagi=_U,
                              iou=_U, birim="hucre", n=504,
                              not_="optimizer denetiminin guven esigi yoktur"),
    "parametre_nc2":     dict(kaynak="parametre_nc2", esik=_U, esik_kaynagi=_U, iou=_U,
                              birim="parametre sayisi", nc=2,
                              not_="CERCEVE nc'dir: nc=80 yayimli degerler farkli oran verir"),
    "belirlenimcilik":   dict(kaynak="kohortB_seed30+capraz_makine", esik="conf 0,001",
                              esik_kaynagi="kolon", iou="0,5 (kolon)",
                              birim="puan ve tensor sayisi"),
    "esli_rejim_farki":  dict(kaynak="band_csv", esik="conf 0,001", esik_kaynagi="dosya_adi",
                              iou="kayitta yok", birim="kosum (tohum-esli)", n=30),
    "kohort_C":          dict(kaynak="kohort_C", esik="conf 0,001", esik_kaynagi="kolon",
                              iou="0,5 (kolon)", birim="kosum", n=30),
    "heldout_altkume":   dict(kaynak="heldout_altkume", esik="conf 0,001", esik_kaynagi="kolon",
                              iou="0,5 (ardisik duzen)", birim="hucre", n=22),
    "ikiz_egitim":       dict(kaynak="ikiz_egitim", esik="conf 0,001", esik_kaynagi="kolon",
                              iou="0,5 (kolon)", birim="konfigurasyon", n=39),
    "kohortB_esikler":   dict(kaynak="kohortB_seed30", esik="conf 0,001 VE 0,25 (ayri kalem)",
                              esik_kaynagi="kolon", iou="0,5 (kolon)", birim="kosum", n=30),
    # Kaynagi CSV degil CAGDAS KAYIT olan blok: _kaynaklar'da anahtari yok, kayit
    # dosya+satir olarak verilir. kaynak alani bos birakilir ki kaynak denetimi
    # yanlis "cozulemeyen anahtar" uretmesin.
    "degerlendirme_hatti": dict(kaynak="", esik="conf 0,001", esik_kaynagi="cagdas_kayit",
                              iou="0,5", birim="puan", parti="DEGISKEN: 1 / 16 / kanonik",
                              kayit="_capsule_repo_hazirlik/PLAN_makale_20261003.md:2907",
                              not_="cerceveye DORDUNCU boyut: degerlendirme parti boyutu"),
    # veri/ aday listeye eklenince geri gelen uc blok (bkz. _ham_adaylari duzeltmesi):
    # cerceve ham CSV'nin KOLONLARINDAN okunuyor -> en ust kanit basamagi.
    "izgara":            dict(kaynak="izgara_ham", esik="conf %s" % IZGARA_CONF, esik_kaynagi="kolon",
                              iou="%s (kolon)" % IZGARA_IOU, birim="model",
                              parti="KAYITTA YOK",
                              makine="KOLONDA; yapilandirma atamasiyla KARISMIS -- grup ortalamalari karsilastirilamaz (bkz. _izgara_makine_karismasi)",
                              kayit="veri/C3TR_kanonik_768.csv",
                              not_="ham kosum ciktisi; conf/iou dosyada KOLON olarak var"),
    "izgara_ozet":       dict(kaynak="izgara_ham", esik="conf %s" % IZGARA_CONF, esik_kaynagi="kolon",
                              iou="%s (kolon)" % IZGARA_IOU, birim="model",
                              parti="KAYITTA YOK",
                              makine="KOLONDA; yapilandirma atamasiyla KARISMIS -- grup ortalamalari karsilastirilamaz (bkz. _izgara_makine_karismasi)",
                              kayit="veri/C3TR_kanonik_768.csv"),
    "_izgara_makine_karismasi": dict(kaynak="izgara_ham", esik="conf %s" % IZGARA_CONF,
                              esik_kaynagi="kolon", iou="%s (kolon)" % IZGARA_IOU,
                              birim="model", parti="KAYITTA YOK",
                              makine="KOLONDA (4 makine; yapilandirma atamasiyla KARISMIS)",
                              not_="MAKINE yeni cerceve boyutu; parti'nin ayni bicimi"),
    "ortalama_disiplini": dict(kaynak="ek6_sinif_csv", esik="conf 0,001",
                              esik_kaynagi="beyan", iou="0,5 (ardisik duzen)",
                              birim="hucre", n=504, parti="KAYITTA YOK",
                              not_="SEKIZINCI BOYUT: makro/mikro; 504/504 olculdu"),
    # Olculmemis bir kalemin kutuk girdisi de durust olmali: cercevesi UYGULANMAZ
    # cunku bir olcum degil, bir OLCUM YOKLUGU kaydi.
    "alanyazin_bildirim_orani": dict(kaynak="", esik=_U, esik_kaynagi=_U, iou=_U,
                              birim=_U, parti=_U, kayit="OLCUM YOKLUGU kaydi",
                              not_="olculmedi; derlemenin sessizligi kaynaklarin sessizligi degil"),
    "veri_kumesi": dict(kaynak="", esik=_U, esik_kaynagi=_U, iou=_U, birim="kutu",
                              parti=_U, kayit="damla_makale/dataset/*/labels/*.txt",
                              not_="etiket dosyalarindan dogrudan sayildi"),
    "olumsuz_sonuc_esik_cikarimi": dict(kaynak="kohortB_seed30",
                              esik="conf 0,001 VE 0,25 (karsilastirilan)", esik_kaynagi="kolon",
                              iou="0,5 (kolon)", birim="kosum", n=30,
                              not_="OLUMSUZ SONUC kaydi: P/R uzerinden esik cikarimi ayirt etmiyor"),
}
# DEMIRIN IKINCI SURUMU (Mac-inceleme bulgusu [1]): ilk surum BEYANIN VERI KILIGINA
# GIRMESIYLE tatmin edilebiliyordu. _ikiz_egitim'e ekledigim IoU/Conf kolonlari 39
# satirda SABIT; sabit bir kolon, "her kosumun kaydindan okundu" ile "bilinen deger bir
# kez yazilip yayildi" arasinda AYIRT ETMIYOR. Yani blok "beyan"dan "kolon"a geciyor ve
# denetim yesile donuyor, oysa kanit bir zerre artmiyor.
# NESNEL VE SAHTELENEMEZ OLCUT: cerceve kolonu kaynak dosyada BIRDEN FAZLA deger aliyor
# mu? Aliyorsa kolon olcum dongusunce fiilen degistirilmistir (ayirt edici). Sabitse,
# kanit degeri beyanla aynidir. Bu, benim beyanimdan degil DOSYADAN okunur.
_SIDDET = {"kolon_ayirt_edici": 0, "capraz_baglanti": 1, "cagdas_kayit": 2,
           "kolon_sabit": 3, "dosya_adi": 4, "beyan": 5, "yok": 6}
_SIDDET_AD = {0: "kosum dongusunce degistirilmis kolon (en guclu)",
              1: "capraz baglanti: deger, ayirt edici cerceve kolonu TASIYAN bir dosyadaki "
                 "satirla BIREBIR esit -- cerceve beyanla degil OLCUMLE kuruluyor",
              2: "cagdas surumlu protokol kaydi: olcum aninda, ekleme-yalniz ve surumlu "
                 "bir belgeye yazilmis tam protokol (dosya+satir verilir). Komut degil, "
                 "ama sonradan hatirlama da degil",
              3: "sabit kolon -- kanit degeri BEYANLA AYNI",
              4: "dosya adindan (H78 sinifi: kimligi addan okumak)",
              5: "ardisik duzen beyani (H78 sinifi)",
              6: "HICBIR KAYITTA YOK"}

def _kolon_sinifi(kaynak_anahtari):
    """Kaynak dosyada cerceve kolonu var mi, varsa ayirt edici mi -- DOSYADAN olcer."""
    _kk = K["_kaynaklar"].get(kaynak_anahtari)
    if not _kk: return None
    _yy = _kk.get("depo_yolu") or _kk.get("yol")
    if not _yy or not os.path.exists(_yy): return None
    try:
        with open(_yy, newline="", encoding="utf-8", errors="replace") as _fh:
            _rr = list(csv.DictReader(_fh))
    except Exception:
        return None
    if not _rr: return None
    _cols = [c for c in _rr[0] if c and c.strip().lower() in ("conf", "iou", "confidence")]
    if not _cols: return None
    _ayirt = any(len(set((x.get(c) or "") for x in _rr)) > 1 for c in _cols)
    return "kolon_ayirt_edici" if _ayirt else "kolon_sabit"

# Sampiyonun yeniden degerlendirmesi: capraz baglanti zincirinin orta halkasi.
# Kaynak olarak kaydedilmezse zincir kurulamaz (ilk denemede oyle oldu).
_ry, _yy2 = _oku("_sampiyon_seed00_yeniden_degerlendirme_155_20261013.csv")
if _ry:
    K["_kaynaklar"]["sampiyon_yeniden"] = {"yol": _yy2, "md5": sha(_yy2)}

# CAPRAZ BAGLANTI SINAYICISI (Mac-inceleme [1]'e olculmus yanit): cerceve kolonu
# olmayan bir dosyadaki deger, AYIRT EDICI cerceve kolonu tasiyan bir dosyadaki
# satirla alti hane duyarlikta BIREBIR esitse, iki olcum ayni cerceveden gelir.
# Alti haneli bir mAP degerinin rastlantiyla eslesme olasiligi ihmal edilebilir;
# ustelik bu sinama YATIRILAN DOSYALARDAN herkes tarafindan yeniden kosulabilir.
# Bu bir BEYAN DEGIL: iddiayi ben yazmiyorum, dosyalar veriyor.
def _sayi_mi(v):
    try:
        _fv = float(v)
        return 0.0 < _fv <= 1.0 and len(str(v).split(".")[-1]) >= 6
    except Exception:
        return False

# CAPRAZ BAGLANTI SINAYICISI, UCUNCU SURUM.
# Birinci surum: tek deger eslesmesi -> bvl_csv TEK eslesmeyle demirlendi, 478 degeri
#   havuza girdi, ikiz_egitim o sahte havuza 24 kez eslesip yukseldi. SAHTE.
# Ikinci surum: rastlanti tabani (eslesme>=2, oran>=10) -> bvl ve ikiz dogru sekilde
#   reddedildi, ama ayristirma30 ucu DAGINIK eslesmeyle (R <-> mAP5095 <-> AP_benign,
#   hepsi alakasiz bir dosyanin alakasiz kolonlarina) tabanin ustunde kaliyordu. Oran
#   testi KOLON KIMLIGINI gormuyor.
# Ucuncu surum -- OLCUT SATIR KIMLIGI: iki dosyanin birer satiri, AYNI ADLI en az IKI
#   sayisal kolonda alti hane duyarlikta ESITSE, o iki satir ayni olcumden gelir.
#   Tek kolon rastlantisi sik, iki kolonun ayni satirda birden tutmasi degil
#   (~1e-12 mertebesi). Bu sinama yatirilan dosyalardan herkes tarafindan kosulabilir
#   ve BEYANLA TATMIN EDILEMEZ: kolon yazmak satir kimligi uretmez.
_ESIK_KOL = ("conf", "confidence")

def _dosya_satirlari(kaynak_anahtari):
    _kk = K["_kaynaklar"].get(kaynak_anahtari)
    if not _kk: return None, None
    _yy = _kk.get("depo_yolu") or _kk.get("yol")
    if not _yy or not os.path.exists(_yy): return None, None
    try:
        with open(_yy, newline="", encoding="utf-8", errors="replace") as _fh:
            _rr = list(csv.DictReader(_fh))
    except Exception:
        return None, None
    if not _rr: return None, None
    _ck = next((c for c in _rr[0] if c and c.strip().lower() in _ESIK_KOL), None)
    return _rr, _ck

def _satir_sayilari(x, ck):
    return {c: round(float(v), 6) for c, v in x.items()
            if c and c != ck and v and _sayi_mi(v)}

def _satir_kimligi(aday_anahtari, havuz_anahtarlari, en_az=2):
    """Aday dosyanin bir satiri, havuz dosyalarinin bir satiriyla ayni adli >=2
    kolonda birebir esit mi? Esitse o satirin esigini dondurur."""
    _ar, _ack = _dosya_satirlari(aday_anahtari)
    if not _ar: return None
    _bulgular = []
    for _hk in havuz_anahtarlari:
        if _hk == aday_anahtari: continue
        _hr, _hck = _dosya_satirlari(_hk)
        if not _hr: continue
        for _ax in _ar:
            _a = _satir_sayilari(_ax, _ack)
            if len(_a) < en_az: continue
            for _hx in _hr:
                _h = _satir_sayilari(_hx, _hck)
                _ortak = [c for c in _a if c in _h and _a[c] == _h[c]]
                if len(_ortak) >= en_az:
                    _bulgular.append({
                        "aday_satir": {k: _ax.get(k) for k in list(_ax)[:1]},
                        "havuz_dosyasi": _hk,
                        "esit_kolonlar": sorted(_ortak),
                        "esit_kolon_sayisi": len(_ortak),
                        "havuz_esigi": ((_hx.get(_hck) or "").strip() if _hck else None),
                    })
    if not _bulgular: return None
    _esikler = sorted(set(b["havuz_esigi"] for b in _bulgular if b["havuz_esigi"]))
    return {"bulgu_sayisi": len(_bulgular), "ornekler": _bulgular[:3],
            "esikler": _esikler, "tekil_esik": _esikler[0] if len(_esikler) == 1 else None,
            "olcut": "satir kimligi: ayni adli >=%d kolonda birebir esitlik" % en_az}

# 1. ATLAMA: ayirt edici cerceve kolonu TASIYAN dosyalar
_AYIRT = [a for a in K["_kaynaklar"] if _kolon_sinifi(a) == "kolon_ayirt_edici"]
# 2. ATLAMA: 1. atlamadaki bir dosyayla satir kimligi kuran dosyalar (esikleri devralir)
_ARA = {}
for _a in K["_kaynaklar"]:
    if _a in _AYIRT: continue
    _sk = _satir_kimligi(_a, _AYIRT)
    if _sk and _sk.get("tekil_esik"): _ARA[_a] = _sk
_IKINCI = len(_ARA)

def _capraz_baglanti(kaynak_anahtari):
    """Kaynagin degerleri, ayirt edici dosyalardaki degerlerle birebir esliyor mu?"""
    _kk = K["_kaynaklar"].get(kaynak_anahtari)
    if not _kk: return None
    _yy = _kk.get("depo_yolu") or _kk.get("yol")
    if not _yy or not os.path.exists(_yy): return None
    try:
        with open(_yy, newline="", encoding="utf-8", errors="replace") as _fh:
            _rr = list(csv.DictReader(_fh))
    except Exception:
        return None
    _bul = []
    for _x in _rr:
        for _c, _v in _x.items():
            if not _v: continue
            try: _fv = float(_v)
            except Exception: continue
            if not (0.0 < _fv <= 1.0) or len(str(_v).split(".")[-1]) < 6: continue
            _e = _HAVUZ.get(round(_fv, 6))
            if _e:
                _bul.append({"deger": round(_fv, 6), "kolon": _c,
                             "eslesen": sorted(set((a, b) for a, b, _ in _e))})
    if not _bul: return None
    _bek2 = (len(set(round(float(v), 6) for _x in _rr for _c, v in _x.items()
                     if v and _c and _sayi_mi(v))) * len(_HAVUZ)) / 1e6
    _tekil = set(z["deger"] for z in _bul)
    _oran2 = (len(_tekil) / _bek2) if _bek2 > 0 else float("inf")
    if len(_tekil) < 2 or _oran2 < 10:
        return {"REDDEDILDI": "rastlanti tabanini gecemedi",
                "tekil_eslesme": len(_tekil), "beklenen_rastlanti": round(_bek2, 3),
                "oran": round(_oran2, 2), "esik_karari": None, "tekil_esik": None}
    _esikler = sorted(set(b for z in _bul for _, b in z["eslesen"]))
    _at = max((_ATLAMA.get(z["deger"], 1) for z in _bul), default=1)
    return {"eslesme_sayisi": len(_bul), "tekil_eslesme": len(_tekil),
            "beklenen_rastlanti": round(_bek2, 3), "oran": round(_oran2, 1), "esikler": _esikler,
            "ornekler": _bul[:3], "atlama": _at,
            "atlama_notu": ("dogrudan ayirt edici kolona" if _at == 1 else
                            "ara dosya uzerinden (iki atlama) -- kanit bir kademe zayif"),
            "tekil_esik": _esikler[0] if len(_esikler) == 1 else None}

# [1] YEDINCI BOYUT BUTUN KUTUGE EKLENIR (Mac-inceleme bulgusu):
# degerlendirme partisi kesfedildiginde yalniz onu kesfeden bloga yazilmisti; kutuk
# "yedi boyut sayip altisini denetliyor" durumuna dusmustu. Bu H63'un aynisi: kutugun
# TASIMADIGI bir boyut kutuge GORUNMEZ. Simdi 18 girdinin hepsinde alan var ve
# cogunda durust cevap "KAYITTA YOK".
# DORDUNCU BOYUT ATEŞLEMESI (19.10): cerceve kutugunun ILAN EDILMIS kor noktasi
# ("boyut listesi KAPALI DEGIL") bugun dorduncu kez ateşledi. Sirayla: parti -> makine
# -> duyarlik -> SURUCU. dnnlab1 tartismasinda cikti: ayni kart, ayni CUDA derlemesi,
# FARKLI SURUCU bir makine ciftini "makine (x) surucu" yapiyor. Ve M3'un kendi capraz
# makine olcumunde surucu HER IKI UCTA DA KAYITLI DEGIL.
_SURUCU_BILINEN = {
    "cozulen_optimizer": _U, "parametre_nc2": _U, "veri_kumesi": _U,
    "alanyazin_bildirim_orani": _U,
}

_PARTI_BILINEN = {
    "degerlendirme_hatti": "DEGISKEN: 1 / 16 / EK6 (EK6'nin duzeyi bilinmiyor)",
    # [D2] Mac-inceleme: karma DUZYAZI iki ayri bolunti uretiyordu -- benim kuralim
    # "kismen kayitli => kayitli", bir sayacin kurali "metinde KAYITTA YOK var => yok".
    # Ikisi de savunulabilir, ama kayit hangisini kullandigini BEYAN ETMIYORDU. Alan
    # yapilandirildi; ozet artik TURETILIYOR, elle yazilmiyor.
    "ayristirma_kolu": {"durum": "kismi", "deger": 1, "donanim": "155/CPU",
                        "kayitli_satir": 1, "kayitta_yok_satir": 29,
                        "not_": "yalniz kopru satiri (tohum 0) olculdu"},
    "capraz_makine": {"durum": "kismi", "deger": 1, "donanim": "155/CPU",
                      "kayitli_satir": 1, "kayitta_yok_satir": 1,
                      "not_": "dnnlab3_sampiyon satiri olculdu; 155_caprazmakine icin yok"},
    "cozulen_optimizer": _U,
    "parametre_nc2": _U,
}
for _k4 in _CERCEVE:
    if "surucu" not in _CERCEVE[_k4]:
        _CERCEVE[_k4]["surucu"] = _SURUCU_BILINEN.get(_k4, "KAYITTA YOK")
    if "parti" not in _CERCEVE[_k4]:
        _CERCEVE[_k4]["parti"] = _PARTI_BILINEN.get(_k4, "KAYITTA YOK")
    elif _k4 in _PARTI_BILINEN:
        _CERCEVE[_k4]["parti"] = _PARTI_BILINEN[_k4]

_cd = {"cerceveler": {}, "kutuksuz_blok": [], "kaynak_bulunamadi": [], "siniflar": {}}
for _k, _v in K.items():
    if _k.startswith("_") or not isinstance(_v, dict): continue
    _c = _CERCEVE.get(_k)
    if _c is None:
        _cd["kutuksuz_blok"].append(_k); continue
    _c = dict(_c)
    for _ka in str(_c.get("kaynak", "")).split("+"):
        if _ka and _ka not in K["_kaynaklar"]:
            _cd["kaynak_bulunamadi"].append({"blok": _k, "kaynak": _ka})
    if not str(_c.get("kaynak", "")).strip() and not _c.get("kayit"):
        _cd["kaynak_bulunamadi"].append({"blok": _k, "kaynak": "ne CSV ne cagdas kayit"})
    # BEYAN EDILEN sinifi DOSYADAN olculenle karsilastir; dosya kazanir
    _beyan = str(_c.get("esik_kaynagi", ""))
    if _beyan == _U:
        _sinif = None
    else:
        _olculen = None
        for _ka in str(_c.get("kaynak", "")).split("+"):
            _o = _kolon_sinifi(_ka)
            if _o and (_olculen is None or _SIDDET[_o] < _SIDDET[_olculen]): _olculen = _o
        if _olculen is None or _SIDDET[_olculen] > _SIDDET["capraz_baglanti"]:
            for _ka in str(_c.get("kaynak", "")).split("+"):
                if not _ka: continue
                # 1. ATLAMA: dogrudan ayirt edici dosyaya satir kimligi
                _sk1 = _satir_kimligi(_ka, _AYIRT)
                if _sk1 and _sk1.get("tekil_esik"):
                    _olculen = "capraz_baglanti"
                    _c["capraz_baglanti"] = dict(_sk1, atlama=1,
                        atlama_notu="dogrudan ayirt edici kolon tasiyan dosyaya satir kimligi")
                    break
                # 2. ATLAMA: ara dosyaya satir kimligi; esik ARA DOSYADAN DEVRALINIR.
                # (Ilk yazimda esigi eslesen satirin conf kolonundan okumaya calistim;
                # ara dosyanin conf kolonu YOK, bu yuzden zincir sessizce kopuyordu.)
                _sk2 = _satir_kimligi(_ka, list(_ARA))
                if _sk2:
                    _dev = sorted(set(_ARA[_b["havuz_dosyasi"]]["tekil_esik"]
                                      for _b in _sk2["ornekler"]
                                      if _b["havuz_dosyasi"] in _ARA))
                    if len(_dev) == 1:
                        _olculen = "capraz_baglanti"
                        _c["capraz_baglanti"] = dict(_sk2, atlama=2, devralinan_esik=_dev[0],
                            tekil_esik=_dev[0],
                            atlama_notu=("ara dosya uzerinden satir kimligi (iki atlama); "
                                         "esik ara dosyadan devralindi"))
                        # IKINCI ATLAMANIN DOSYA DUZEYI VARSAYIMI BAGIMSIZ KAPANDI:
                        # kopru dosyasinin protokolu olcum aninda PLAN'a yazilmis.
                        _c["ek_kanit"] = {
                            "sinif": "cagdas_kayit",
                            "kayit": "_capsule_repo_hazirlik/PLAN_makale_20261003.md:2740 ve :2804",
                            # Mac-inceleme [3]: PLAN bu depoda DEGIL, yayin deposuna da
                            # yatirilmayacak. Sarkan bir gonderme KANIT GIBI GORUNUR ve
                            # durust bir beyandan KOTUDUR. Cozum dosyayi tasimak degil,
                            # basamagi KENDI KENDINI BELGELEYECEK hale getirmek: commit
                            # SHA + yazar tarihi + alinti, sayiyla birlikte yolculuk eder.
                            "commit_sha": "94108279004326aa02f463c68c6bcd78995bb39b",
                            "yazar_tarihi": "2026-10-13 13:40:04 +0300",
                            "alinti": ("tek protokolde (155, CPU, conf 0,001 / IoU 0,5) "
                                       "yeniden degerlendirme: 0,799009 <-> 0,685227"),
                            "on_kayit_savi": ("Basamagi 'beyan'in ustune cikaran sey olcumle "
                                              "cagdas olmasi DEGIL, cerceve demirinin HENUZ "
                                              "VAR OLMADIGI bir anda yazilmis olmasi: kayit "
                                              "13.10 13:40, demir 18.10 00:00 (commit 00fb567). "
                                              "Dort gun oncesinde yazilan bir satir, henuz icat "
                                              "edilmemis bir denetimi tatmin etmek icin "
                                              "yazilmis olamaz."),
                            "demir_commit": "00fb567",
                            "demir_tarihi": "2026-10-17T23:59:55+03:00",
                            "on_kayit_marji_gun": 4.4,
                            # [E] Mac-inceleme kendi onerisini zayiflatti: SHA savi
                            # YANLISLANABILIR kilar (depo bir gun yayimlanirsa yanlis sav
                            # yakalanir) ama DOGRULANABILIR kilmaz -- kaynak depo
                            # yatirilmiyor. Iki ayri epistemik durum; hangisinde oldugu
                            # yazilir.
                            "durum": ("yanlislanabilir; DOGRULANABILIR DEGIL -- kaynak depo "
                                      "(_capsule_repo_hazirlik) yatirilmiyor"),
                            "dogrulanabilirlige_yukseltme": ("arsive kucuk bir metin dosyasi: "
                                      "alinti + `git log -1 --format='%H %aI'` cikti + dosyanin "
                                      "`git hash-object` blob hash'i. O zaman sarkan gonderme "
                                      "yerine, depo yayimlandiginda ESLESMEK ZORUNDA olan bir "
                                      "hash kalir. (Mac-inceleme [E]; gonderim sonrasi.)"),
                            "yazili_protokol": "155, CPU, conf 0,001 / IoU 0,5",
                            "etki": ("ikinci atlamanin 'ayni dosya => ayni cerceve' varsayimi "
                                     "artik gerekli DEGIL: kopru dosyasinin protokolu bagimsiz "
                                     "bir cagdas kayitta duruyor. Varsayim kaldirilmadi, "
                                     "GEREKSIZLESTI."),
                            "kaynak_turu": "ekleme-yalniz, surumlu, olcum aninda yazilmis",
                        }
                        break
        if _beyan == "kolon":
            # BEYANIMI DOGRULA: kolon gercekten ayirt edici mi?
            _sinif = _olculen or "yok"
            if _olculen is None:
                _c["beyan_duzeltildi"] = "kolon dendi ama kaynak dosyada cerceve kolonu YOK"
            elif _olculen == "kolon_sabit":
                _c["beyan_duzeltildi"] = ("kolon dendi; kolon VAR ama SABIT -- kanit degeri "
                                          "beyanla ayni (Mac-inceleme [1])")
        else:
            # kolon iddia etmiyorum; ama dosyada ayirt edici kolon varsa yukselt
            _sinif = _olculen if (_olculen and _SIDDET[_olculen] < _SIDDET[_beyan]) else _beyan
    _c["cerceve_kaniti"] = _sinif
    _c["cerceve_kaniti_aciklama"] = (_SIDDET_AD.get(_SIDDET.get(_sinif), "") if _sinif else _U)
    _cd["cerceveler"][_k] = _c
    _cd["siniflar"].setdefault(_sinif or _U, []).append(_k)

_zayif = [b for sn in ("kolon_sabit", "dosya_adi", "beyan", "yok") for b in _cd["siniflar"].get(sn, [])]
_tasiyici_zayif = [b for b in _cd["siniflar"].get("yok", [])]
_cd["olcum"] = {sn: len(_cd["siniflar"].get(sn, [])) for sn in
                ("kolon_ayirt_edici", "kolon_sabit", "dosya_adi", "beyan", "yok", _U)}
_cd["zayif_cerceveli_blok"] = _zayif
# PARTI DENETIMI: kac girdide kayitli, kacinda yok. Yesile cekilmez, sayilir.
_pb = {"kayitli": [], "kayitta_yok": [], "uygulanmaz": []}
_pb["kismi"] = []
for _k5, _v5 in _cd["cerceveler"].items():
    _pv = _v5.get("parti", "")
    if isinstance(_pv, dict):
        (_pb["kismi"] if _pv.get("durum") == "kismi" else _pb["kayitli"]).append(_k5)
        continue
    _pv = str(_pv)
    if _pv == _U: _pb["uygulanmaz"].append(_k5)
    elif _pv == "KAYITTA YOK" or not _pv: _pb["kayitta_yok"].append(_k5)
    else: _pb["kayitli"].append(_k5)
_cd["parti_denetimi"] = dict(_pb, ozet=("parti boyutu: %d TAM kayitli, %d KISMI (bir satir "
    "olculdu, dosya geneli yok), %d KAYITTA YOK, %d uygulanmaz -- toplam %d"
    % (len(_pb["kayitli"]), len(_pb["kismi"]), len(_pb["kayitta_yok"]),
       len(_pb["uygulanmaz"]), len(_cd["cerceveler"]))),
    sayma_kurali=("KISMI ayri sayilir. Onceki surum 'kismen kayitli => kayitli' sayiyordu ve "
                  "ozet elle yaziliydi; bagimsiz bir sayac farkli bolunti uretiyordu "
                  "(Mac-inceleme [D2]). Ozet artik alanlardan TURETILIYOR."),
    gerekce=("Cerceve yedi boyutlu ilan edildi; bu alan yedincisinin KAC girdide fiilen "
             "belgelendigini sayar. Kutugun tasimadigi boyut kutuge gorunmez (H63)."))

# SURUCU DENETIMI: dorduncu boyut, parti ile ayni bicimde sayilir
_sb = {"kayitli": [], "kayitta_yok": [], "uygulanmaz": []}
for _k9, _v9 in _cd["cerceveler"].items():
    _sv = str(_v9.get("surucu", ""))
    if _sv == _U: _sb["uygulanmaz"].append(_k9)
    elif _sv == "KAYITTA YOK" or not _sv: _sb["kayitta_yok"].append(_k9)
    else: _sb["kayitli"].append(_k9)
_cd["surucu_denetimi"] = dict(_sb, ozet=("surucu surumu %d girdide kayitli, %d girdide YOK, "
    "%d girdide uygulanmaz" % (len(_sb["kayitli"]), len(_sb["kayitta_yok"]), len(_sb["uygulanmaz"]))),
    gerekce=("Dorduncu boyut atesleme. Ayni kart + ayni CUDA derlemesi + FARKLI SURUCU bir "
             "makine ciftini 'makine (x) surucu' yapar; M3'un capraz makine olcumunde surucu "
             "her iki ucta da kayitli DEGIL, dolayisiyla eksenin ucuncu bir etken tasiyip "
             "tasimadigi BILINMIYOR."))

_cd["havuz"] = {
    "ayirt_edici_dosyalar": _AYIRT,
    "ara_dosyalar": {_k3: _v3.get("tekil_esik") for _k3, _v3 in _ARA.items()},
    "not_": "ayirt edici = cerceve kolonu dosyada BIRDEN FAZLA deger aliyor. ara = o "
            "dosyalardan biriyle SATIR KIMLIGI kuran dosya; esigi devralir.",
    "varsayim": "Ikinci atlama DOSYA DUZEYINDE bir varsayim tasir: ara dosyanin bir satiri "
                "ayirt edici dosyaya demirlendiginde, AYNI DOSYANIN oteki satirlari da ayni "
                "cerceveden sayilir (ayni degerlendirme turu). Bu varsayim beyan edilir, "
                "gizlenmez; kirilabilecegi hal, bir dosyanin farkli esiklerde olculmus "
                "satirlari TEK dosyada toplamasidir. sampiyon_yeniden icin iki satir da ayni "
                "turda (sampiyon ve seed00'in ozdes protokolden yeniden gecirilmesi).",
}
_cd["kapsam"] = ("Kutuge kayitli her olcum blogunun CERCEVE KANIT SINIFI: cercevenin "
                 "NEREDEN geldigi (kolon / capraz baglanti / cagdas kayit / dosya adi / "
                 "beyan / yok) ve kaynak anahtarinin _kaynaklar'da cozulup cozulmedigi.")
_cd["kapsam_disi"] = [
    "CERCEVENIN DOGRU OLUP OLMADIGI: sinif yalniz kanitin TURUNU soyler. Bir kolon "
    "ayirt edici olabilir ve yine de yanlis esik tasiyabilir",
    "KUTUKTE OLMAYAN BIR BOYUT: kutuk yedi boyut sayiyor ama boyut listesi KAPALI "
    "DEGIL -- 18.10'da parti, makine ve duyarlik UC AYRI TURDA eklendi. Sekizinci "
    "boyut bu demire GORUNMEZ olur (H63 / H95)",
    "BLOK ICERIGININ DOGRULUGU: bir blok dogru cerceveyle yanlis sayi tasiyabilir; "
    "onu --dogrula ve ham veri denetimi kapsar, bu demir kapsamaz",
    "VERI BOLUNMESI: egitim/test ayriminin kimligi cerceve boyutu olarak KAYITLI DEGIL",
]
_cd["gecti"] = (not _cd["kutuksuz_blok"] and not _cd["kaynak_bulunamadi"] and not _zayif)
_cd["ozet"] = ("CERCEVE DEMIRI GECTI" if _cd["gecti"] else
               "CERCEVE DEMIRI GECMEDI: %d blokta cerceve kaniti beyan duzeyinde ya da yok "
               "(bunlarin %d'inde HICBIR KAYITTA YOK)" % (len(_zayif), len(_tasiyici_zayif)))
_cd["gerekce"] = ("Demir BEYANLA TATMIN EDILEMEZ: 'kolon' iddiasi dosyadan dogrulanir ve "
                  "kolon SABITSE sinif dusurulur, cunku sabit kolon 'okundu' ile 'yayildi' "
                  "arasinda ayirt etmez (Mac-inceleme [1]). Siddet sirasi: ayirt edici kolon > "
                  "sabit kolon > dosya adi > beyan > yok. Son ikisi H78 ile ayni epistemik "
                  "siniftadir: kimligi addan/aliskanliktan okumak.")
_cd["acik_kalan_is"] = ("ayristirma_kolu ve capraz_makine cerceveleri HICBIR KAYITTA YOK ve "
                        "en cok yuk tasiyan iki blok (§3.3 varyans ayrisimi; ozdeki 9,68). "
                        "Tek care cerceve kolonlariyla YENIDEN OLCUM; dnnlab3 gerekir.")
K["_cerceve_denetimi"] = _cd

# IZLENEBILIRLIK (17.10, Mac-inceleme bulgusu [b]): mutlak yol baska makinede/hakemde/Zenodo'da
# cozulmez; ayrica core.autocrlf=input etkin oldugundan CALISMA KOPYASINDAN alinan md5, DEPOYA
# islenen bayt dizisiyle tutmayabilir (CRLF -> LF). Her kaynaga depo-goreli yol eklenir ve md5
# depo blob'una karsi ATEŞLENEN bir kontrolle dogrulanir; uyusmazlik kayda yazilir, sessiz gecmez.
try:
    _DEPO = subprocess.run(["git","-C",os.path.abspath(OUT),"rev-parse","--show-toplevel"],
                           capture_output=True,text=True).stdout.strip() or os.path.dirname(os.path.abspath(OUT))
except Exception:
    _DEPO = os.path.dirname(os.path.abspath(OUT))
def _depo_goreli(y):
    try:
        r = os.path.relpath(os.path.abspath(y), _DEPO)
        return r if not r.startswith("..") else None
    except Exception:
        return None
def _git_blob_md5(rel):
    if not rel: return None
    try:
        r = subprocess.run(["git","-C",_DEPO,"show","HEAD:"+rel],capture_output=True)
        return hashlib.md5(r.stdout).hexdigest()[:12] if r.returncode==0 and r.stdout else None
    except Exception:
        return None
_izlenebilirlik = {"uyusmayan": [], "izlenmeyen": []}
for _k, _v in K["_kaynaklar"].items():
    if not isinstance(_v, dict) or not _v.get("yol"): continue
    _rel = _depo_goreli(_v["yol"])
    _v["depo_yolu"] = _rel
    # ADRESIN KIMLIGI KOKUNU DE ICERIR (Mac-inceleme 18.10): 'yol' mutlak ve bu
    # makineye ozgu; arsivi indiren okur /home/dnnlab7/... goren yerde arsivdeki
    # veri/X.csv oldugunu TAHMIN etmek zorunda kaliyordu. Bayt orada, ADRES
    # OKUNAMAZ. H89 hash icin "referans noktasi beyan edilmeden anlamsiz" diyor;
    # yol icin ayni: kokü beyan edilmeden yol anlamsiz. Mutlak yol ayri alana
    # tasinir ve tasinabilir OLMADIGI etiketlenir.
    _v["yerel_yol"] = {"makine": "155", "yol": _v["yol"], "tasinabilir": False,
                       "not_": "arsivde cozulmez; adres olarak depo_yolu kullanilir"}
    _v["yol"] = _rel or _v["yol"]
    # TAM sha256: kirpilmis md5'in (48 bit) yaninda, kamuya acik arsiv icin
    _v["sha256"] = _sha256(_v["yerel_yol"]["yol"])
    _gb = _git_blob_md5(_rel)
    _v["depo_blob_md5"] = _gb
    if _gb is None:
        _v["depodan_dogrulanabilir"] = False
        _izlenebilirlik["izlenmeyen"].append(_k)
    elif _gb != _v.get("md5"):
        _v["depodan_dogrulanabilir"] = False
        _izlenebilirlik["uyusmayan"].append({"kaynak": _k, "calisma_kopyasi": _v.get("md5"), "depo_blob": _gb})
    else:
        _v["depodan_dogrulanabilir"] = True
# DEMIRIN KAPSAMI BEYAN EDILIR (Mac-inceleme 18.10): yukaridaki dongu yalniz
# _kaynaklar'daki HASH'LENEBILIR dosyalari denetliyor. Ama kayitta, _kaynaklar disinda,
# dosya gondermesi yapan baska alanlar da var (PLAN satirlari, model yaml'lari, izgara
# ihraclari, veri kumesi yaml'i). Onlar bu dongunun KAPSAMI DISINDA kaliyordu ve ozet
# "TUM KAYNAKLAR" diyordu -> kayit kendi ozetini curutuyordu. Daha kotusu makine
# okunur taraftaydi: izlenmeyen=[] bir VERI, ve dogrulayici betik "izlenmeyen kaynak yok"
# okuyordu. Katman 0'in kendi ilkesi: ozet alan degil, ALANLARIN FONKSIYONU olmali --
# ve bos bir liste en guclu iddia bicimidir.
_REF = re.compile(r"[A-Za-z0-9_./-]+\.(?:md|csv|py|tex|json|yaml|yml|xlsx|sh)(?::\d+(?:-\d+)?)?")
_SINIF = [
    ("PLAN_makale",            "cagdas_kayit",
     "depo disi; commit SHA + yazar tarihi ile belgelenmis (ek_kanit alanlari)"),
    ("_capsule_repo_hazirlik", "cagdas_kayit",
     "depo disi; commit SHA + yazar tarihi ile belgelenmis (ek_kanit alanlari)"),
    ("models/yolov5",          "kamuya_acik_ucuncu_taraf",
     "ultralytics/yolov5 model tanimi; yaml_md5 alaninda sagiama kayitli, dosya kamuya acik"),
    ("data_4_1.yaml",          "kamuya_acik_veri_yapilandirmasi",
     "INbreast bolunme yapilandirmasi; sinif sayilari veri_kumesi blogunda SAYILMIS halde"),
    ("C3TR_kanonik_768.csv",   "depoda_ad_ile_anilan",
     "dosya DEPODA (veri/C3TR_kanonik_768.csv); kaynak alani yalniz dosya ADINI tasiyor, "
     "depo-goreli yol degil -- okur icin cozulebilir ama belirsiz"),
    ("BIRLESIK_v3_v12_grid",   "turetilmis_veri_depoda",
     "ham izgara ihraclari depo disi; onlardan turetilen veri/_ikiz_egitim CSV'si DEPODA ve hash'li"),
]
def _ref_sinifla(ref):
    for _im, _sn, _ac in _SINIF:
        if _im in ref: return _sn, _ac
    return "siniflandirilmamis", "bu gonderme hicbir sinifa girmedi -- elle incelenmeli"
_izlenen_set = set()
try:
    _izlenen_set = set(subprocess.run(["git", "-C", _DEPO, "ls-files"],
                                      capture_output=True, text=True).stdout.split("\n"))
except Exception:
    pass
def _cozulur_mu(ref):
    _r = ref.split(":")[0]
    if _r in _izlenen_set or _r.lstrip("./") in _izlenen_set: return True
    return os.path.exists(os.path.join(_DEPO, _r))
_disi, _gor = [], set()
def _gez(o, yol=""):
    if isinstance(o, dict):
        for _k6, _v6 in o.items(): _gez(_v6, "%s.%s" % (yol, _k6))
    elif isinstance(o, list):
        for _i6, _v6 in enumerate(o): _gez(_v6, "%s[%d]" % (yol, _i6))
    elif isinstance(o, str):
        if not any(_t in yol.lower() for _t in ("kaynak", "kayit", "yol", "yaml")): return
        for _m6 in _REF.finditer(o):
            _ref = _m6.group(0)
            if _cozulur_mu(_ref): continue
            if (yol, _ref) in _gor: continue
            _gor.add((yol, _ref))
            _sn, _ac = _ref_sinifla(_ref)
            _disi.append({"alan": yol.lstrip("."), "gonderme": _ref, "sinif": _sn,
                          "durum": "DEPO DISI -- hash'lenemez", "aciklama": _ac})
_gez(K)
# IKINCI SINIF: OKUNAMAZ ADRES. Demir simdiye dek yalniz COZULEMEYEN gondermeyi
# yakaliyordu; Mac'in bulgusu farkli bir sinif -- gonderme BENDE cozuluyor, OKURDA
# cozulmuyor. Bayt depoda, adres makineye ozgu. Ayri listelenir.
_MUT = re.compile(r"/home/[A-Za-z0-9_./-]+")
_okunamaz, _gor2 = [], set()
def _gez2(o, yol=""):
    if isinstance(o, dict):
        for _k8, _v8 in o.items(): _gez2(_v8, "%s.%s" % (yol, _k8))
    elif isinstance(o, list):
        for _i8, _v8 in enumerate(o): _gez2(_v8, "%s[%d]" % (yol, _i8))
    elif isinstance(o, str):
        if ".yerel_yol." in yol: return          # beyanli, kasitli
        for _m8 in _MUT.finditer(o):
            if (yol, _m8.group(0)) in _gor2: continue
            _gor2.add((yol, _m8.group(0)))
            _okunamaz.append({"alan": yol.lstrip("."), "gonderme": _m8.group(0),
                              "sinif": "okunamaz_adres",
                              "durum": ("bu makinede COZULUR, arsivi indiren okurda COZULMEZ; "
                                        "bayt depoda ama adres makineye ozgu")})
_gez2(K)
_izlenebilirlik["izlenmeyen"] = _disi
_izlenebilirlik["okunamaz_adres"] = _okunamaz
# KAPSAM_DISI (Mac-inceleme, 18.10): H95 "bir aparat denetlemedigini gorunmez kilar"
# bir TESHIS; tedavisi her kontrolun kendi kor noktasini ILAN ETMESI. Ve soru sinirli
# tutulmali: "neyi gormuyor" sonsuzdur (bir hash denetimi iklim degisikligini de gormez).
# Sinirli hali: "MAKUL BIR OKUR kapsandigini varsayar ama kapsamiyor" -- yani KOMSU
# kategori, uzak kategori degil. Asagidakilerin hepsi o suzgecten geciyor.
_izlenebilirlik["kapsam_disi"] = [
    "DOSYA ICERIGININ DOGRULUGU: hash esleşmesi dosyanin DEGISMEDIGINI soyler, "
    "icindeki sayilarin DOGRU oldugunu soylemez",
    "cagdas-kayit kaynaklari: izlenmeyen listesinde SAYILIR ama icerikleri "
    "DOGRULANMAZ (hash'lenemez, depo disi)",
    "depo disi kamuya acik dosyalarin (model yaml, veri yapilandirmasi) o anda "
    "gercekten o icerikte oldugu -- yalniz kayitli md5 ile kiyaslanabilir",
    "TAAHHUTLER: bir kuyruk kaydinin, bir isin planlandigi gibi kuyruga girdigi. "
    "18.10'da bu kor nokta fiilen gerceklesti (H87 kacagi)",
]
_izlenebilirlik["kapsam"] = (
    "Yukaridaki md5/blob denetimi YALNIZ _kaynaklar'daki hash'lenebilir dosyalari kapsar. "
    "izlenmeyen listesi, kayittaki butun kaynak/kayit alanlari taranarak uretilir ve depodan "
    "cozulemeyen her gondermeyi sinifiyla birlikte tasir.")
_izlenebilirlik["hashlenebilir_sonuc"] = "%d/%d" % (
    sum(1 for _v7 in K["_kaynaklar"].values()
        if isinstance(_v7, dict) and _v7.get("depodan_dogrulanabilir")),
    sum(1 for _v7 in K["_kaynaklar"].values() if isinstance(_v7, dict) and _v7.get("yol")))
# OZET TURETILIR, elle yazilmaz: hash'lenebilir sonuc + depo disi gonderme sayisi.
_izlenebilirlik["ozet"] = (
    "HASH'LENEBILIR KAYNAKLARIN TAMAMI (%s) DEPODAN DOGRULANABILIR"
    % _izlenebilirlik["hashlenebilir_sonuc"]
    + ("" if not _izlenebilirlik["uyusmayan"]
       else "; UYUSMAYAN %d" % len(_izlenebilirlik["uyusmayan"]))
    + ("" if not _okunamaz
       else "; %d alan OKUNAMAZ ADRES tasiyor (mutlak yerel yol -- bkz. okunamaz_adres)"
            % len(_okunamaz))
    + ("; depo disi gonderme YOK" if not _disi
       else "; %d alan DEPO DISI gonderme tasiyor (bkz. izlenmeyen) -- siniflar: %s"
            % (len(_disi), ", ".join(sorted(set(_z["sinif"] for _z in _disi))))))
_izlenebilirlik["gerekce"] = ("Bir dogrulayici icin uyusmayan md5 ile kurcalanmis veri ayirt edilemez; "
    "bu nedenle hash DEPOYA islenen bayt dizisinden dogrulanir, calisma kopyasindan degil. "
    "Kaynak: Mac-inceleme bagimsiz denetimi 17.10.2026, kok neden core.autocrlf=input.")
K["_izlenebilirlik"] = _izlenebilirlik
def _oynaksiz(o):
    """Oynak alanlari cikarir VE sayisal turleri normalize eder.
    Tur normalizasyonu sart (H64): uretici numpy float64 uretirken JSON'dan donen
    deger python float olur; naif karsilastirma 21 SAHTE FARK veriyordu
    ('tur: float -> float64'). Gurultulu bir kapi devre disi birakilir, bu yuzden
    DEGER karsilastirilir, tur degil. Yuvarlama YOK: tam deger korunur (bugunun
    ara-yuvarlama dersi).

    KAPSAM_DISI (ilan edilmis kor noktalar, Mac-inceleme 18.10):
      * URETICININ KENDISININ DOGRULUGU. Bu kapi JSON'un ureticinin CIKTISIYLA ozdes
        oldugunu dogrular; URETICI YANLISSA KAPI YINE GECER. En onemli kor nokta bu.
      * ham CSV'lerin dogrulugu -- kapi onlari okur, sinamaz.
      * KANONIK.md: yalniz JSON karsilastirilir, markdown cikti KARSILASTIRILMAZ.
      * oynak alanlar (_uretim) ve sayisal TURLER kasitli dislanir (asagidaki sart).

    TOLERANS ASLA (Mac-inceleme 18.10): tur normalizasyonu EVET, sayisal tolerans HAYIR.
    Gercek tehdit modeli bariz bir duzenleme degil (99,99), son basamakta TEK HANELI bir
    degisimdir. Sinandi: agirlikli_AP_sampiyon 0,8384905844 -> ...845 (+1e-10) yapildi,
    kapi YAKALADI (1 fark, exit 1). Ileride biri gurultu icin tolerans eklerse kapi tam
    o esikte KOR olur -- gurultunun kaynagi tur farkiydi ve o zaten kapatildi."""
    if isinstance(o, dict):
        return {k: _oynaksiz(v) for k, v in o.items() if k not in _OYNAK}
    if isinstance(o, list):
        return [_oynaksiz(v) for v in o]
    if isinstance(o, bool):
        return o
    try:
        import numbers
        if isinstance(o, numbers.Real) and not isinstance(o, int):
            return float(o)
        if isinstance(o, numbers.Integral):
            return int(o)
    except Exception:
        pass
    return o

_JSON_YOL = os.path.join(OUT, "KANONIK.json")
if _DOGRULA:
    if not os.path.exists(_JSON_YOL):
        print("DOGRULAMA BASARISIZ: %s yok" % _JSON_YOL, file=_sys.stderr); _sys.exit(1)
    with open(_JSON_YOL, encoding="utf-8") as _f:
        _mevcut = json.load(_f)
    _a, _b = _oynaksiz(_mevcut), _oynaksiz(K)
    if _a == _b:
        print("DOGRULAMA GECTI: KANONIK.json ureticinin ciktisiyla ozdes "
              "(oynak alanlar dislandi: %s)" % ", ".join(_OYNAK))
        _sys.exit(0)
    # farki bul ve bildir
    def _fark(x, y, yol=""):
        _o = []
        if type(x) is not type(y):
            return [(yol, "tur: %s -> %s" % (type(x).__name__, type(y).__name__))]
        if isinstance(x, dict):
            for _k in sorted(set(x) | set(y)):
                if _k not in x: _o.append(("%s.%s" % (yol, _k), "DEPODA YOK (uretici ekliyor)"))
                elif _k not in y: _o.append(("%s.%s" % (yol, _k), "URETICIDE YOK (depoda FAZLA -- elle eklenmis olabilir)"))
                else: _o += _fark(x[_k], y[_k], "%s.%s" % (yol, _k))
        elif isinstance(x, list):
            if len(x) != len(y): _o.append((yol, "uzunluk %d -> %d" % (len(x), len(y))))
            else:
                for _i, (_p, _q) in enumerate(zip(x, y)): _o += _fark(_p, _q, "%s[%d]" % (yol, _i))
        elif x != y:
            _o.append((yol, "%r -> %r" % (x, y)))
        return _o
    _ff = _fark(_a, _b)
    print("DOGRULAMA BASARISIZ: KANONIK.json ureticinin ciktisiyla ORTUSMUYOR "
          "(%d fark). Kayit elle duzenlenmis ya da uretici degismis olabilir." % len(_ff),
          file=_sys.stderr)
    for _y, _d in _ff[:25]:
        print("  %s : %s" % (_y.lstrip("."), _d), file=_sys.stderr)
    if len(_ff) > 25: print("  ... %d fark daha" % (len(_ff) - 25), file=_sys.stderr)
    _sys.exit(1)

io = open(_JSON_YOL,"w"); json.dump(K,io,ensure_ascii=False,indent=2); io.close()

# --- insan okunur ---
L=[]
L.append("# KANONİK SAYI KAYDI\n")
L.append("**Üretim:** %s · **Üreten:** `URET_kanonik.py`\n"%K["_uretim"])
L.append("> 🔴 **Bu dosya ELLE DÜZENLENMEZ.** Deney ilerledikçe `python3 URET_kanonik.py` ile yeniden üretilir.")
L.append("> Makalelerde kullanılan her sayı burada bulunmalıdır; bulunmuyorsa kullanılamaz.\n")
L.append("## Ark özetleri (conf 0,001 · mAP@0,5 · %)\n")
L.append("| Ark | n | ort | ss | %95 GA | min–maks | durum |")
L.append("|---|---|---|---|---|---|---|")
for k,v in sorted(K["arklar"].items()):
    L.append("| `%s` | %d | **%.2f** | **%.2f** | %.2f–%.2f | %.1f–%.1f | %s |"%(
        k,v["n"],v["ort"],v["ss"],v["ga_alt"],v["ga_ust"],v["min"],v["maks"],v["durum"]))
L.append("\n## Eşli karşılaştırmalar (puan)\n")
L.append("| Karşılaştırma | n | fark | %95 GA | dz | Wilcoxon p |")
L.append("|---|---|---|---|---|---|")
for k,v in K["esli"].items():
    L.append("| `%s` | %d | **%+.2f** | %+.2f..%+.2f | %.2f | %s |"%(
        k,v["n"],v["fark"],v["ga_alt"],v["ga_ust"],v.get("dz",0),v.get("wilcoxon_p","—")))
L.append("\n## Rejim etkisi (üç rejim eşli)\n")
L.append("| Konfig | n tohum | Friedman χ² | p | Levene p | ss oranı |")
L.append("|---|---|---|---|---|---|")
for k,v in K["rejim_etkisi"].items():
    L.append("| %s | %d | %s | **%s** | **%s** | %s |"%(k,v["n_tohum"],
        v.get("friedman_chi2","—"),v.get("friedman_p","—"),v.get("levene_p","—"),v.get("ss_orani_genis_dar","—")))
if "tekil_zirve" in K:
    t=K["tekil_zirve"]
    L.append("\n## Tekil zirve (92,9) sınaması\n")
    L.append("- toplam koşum: **%d** · band ort **%.2f** (ss %.2f) · band maks **%.2f**"%(t["n_kosum"],t["band_ort"],t["band_ss"],t["band_maks"]))
    L.append("- 92,9'a ulaşan koşum: **%d / %d**"%(t["ulasan_kosum"],t["n_kosum"]))
    L.append("- z-skoru **+%.2f** (map1 kolu, n=30) ⟵ TEZDE KULLANILAN"%t["z_map1"])
    L.append("- z-skoru **+%.2f** (90 koşumun tamamı) — farklı tanım, karıştırma"%t["z_tumu"])
    L.append("\n  ⚠️ %s"%t["NOT"])
if K.get("_kohort_disi"):
    L.append("\n## ⚠️ Kohort dışı koşumlar (seed > %d — bandın parçası DEĞİL)\n"%KOHORT_MAKS_SEED)
    for x in K["_kohort_disi"]:
        L.append("- `%s/%s` seed %d = %.3f (makine %s) — kohort seed 0–%d olduğu için özetlere dahil edilmedi"%(
            x["rejim"],x["konfig"],x["seed"],x["deger"],x["makine"],KOHORT_MAKS_SEED))
if K.get("izgara_ozet"):
    L.append("\n## 256-ızgara (ham koşum çıktısı — 768 model)\n")
    L.append("Kaynak: `C3TR_kanonik_768.csv` · dilim **conf %s / iou %s**. "
             "⚠️ Bu değerler **tezden türetilmemiştir**; ham koşum çıktısındandır.\n"%(IZGARA_CONF,IZGARA_IOU))
    L.append("| Rejim | n | ort | ss | min | maks | en iyi konfig |")
    L.append("|---|---|---|---|---|---|---|")
    for r,v in sorted(K["izgara_ozet"].items()):
        L.append("| %s | %d | **%.2f** | %.2f | %.1f | **%.1f** | `%s` |"%(
            r,v["n"],v["ort"],v["ss"],v["min"],v["maks"],v["en_iyi"]))
    L.append("\n  Tekil konfig değerleri `KANONIK.json` → `izgara.<rejim>.<konfig>` altında.")
if K.get("_izgara_dogrulama"):
    dg=K["_izgara_dogrulama"]
    L.append("\n## Izgara doğrulaması (ham veri ↔ tez eki)\n")
    L.append("- karşılaştırılan hücre: **%d** · ayrışan: **%d** ⇒ **%s**"%(
        dg["karsilastirilan"],dg["ayrisan"],dg["sonuc"]))
    L.append("- yön: `ek2.tex` burada **kaynak değil, sınama hedefidir**; kayıt ham veriden üretilir.")
    for x in dg["ornekler"]:
        L.append("  - ⚠️ `%s/%s` %s: tez %.2f ↔ ham %.2f"%(x["rejim"],x["konfig"],x["alan"],x["tez"],x["ham"]))
if K.get("_uyarilar"):
    L.append("\n## ⚠️ Uyarılar\n")
    for u in K["_uyarilar"]: L.append("- %s"%u)

if K.get("secim_korlugu"):
    _sk = K["secim_korlugu"]
    L.append("\n## Seçim körlüğü — doyma + best/last (v2)\n")
    if _sk.get("doyma_aile_epok"):
        L.append("**Doyma** (eğitim-tepe mAP@0,5; PLATO temiz havuz):\n")
        L.append("| aile·epok | n | ss | benzersiz | ort | >0,99 |")
        L.append("|---|---|---|---|---|---|")
        for _k2, _v2 in _sk["doyma_aile_epok"].items():
            L.append("| `%s` | %d | %.6f | %d | %.4f | %s%% |" % (_k2, _v2["n"], _v2["ss"], _v2["benzersiz"], _v2["ort"], _v2["ust099"]))
        L.append("\n  ⓘ %s" % _sk.get("doyma_ozet", ""))
    if _sk.get("best_last"):
        _b2 = _sk["best_last"]
        L.append("\n**best.pt vs last.pt** (n=%d): ortanca **%+.3f** puan · %%%.1f lehte · Wilcoxon p=**%s**" % (
            _b2["n"], _b2["ortanca_puan"], _b2["yuzde_lehte"], _b2.get("wilcoxon_p", "—")))
        if _b2.get("epok_ortanca"):
            L.append("  epok ortancaları: " + " · ".join("%s→%+.3f" % (e, val) for e, val in _b2["epok_ortanca"].items()) + "  (sönüm)")
if K.get("sinif_bazli"):
    _sb2 = K["sinif_bazli"]
    L.append("\n## Sınıf-bazlı (v2) · %d hücre · %d model\n" % (_sb2.get("n_hucre", 0), _sb2.get("n_model", 0)))
    if _sb2.get("asimetri"):
        _a2 = _sb2["asimetri"]; L.append("- **Sınıf asimetrisi:** %d/%d pozitif · ort **%+.1f puan** (malign>benign). %s" % (_a2["pozitif"], _a2["n"], _a2["ort_puan"], _a2["not_"]))
    if _sb2.get("rho"):
        _r2 = _sb2["rho"]; L.append("- **rho:** genel–iyi **%+.3f** · genel–kötü **%+.3f** · kötü–iyi %+.3f (p=%.3f). %s" % (_r2["genel_iyi"], _r2["genel_kotu"], _r2["kotu_iyi"], _r2["kotu_iyi_p"], _r2["not_"]))
    if _sb2.get("epok_sinif_etkisi"):
        _e2 = _sb2["epok_sinif_etkisi"]; L.append("- **Epok–sınıf etkisi (%s, model n=%d):** iyi **%+.2f** puan (%d poz, p=%s) · kötü **%+.2f** puan (%d poz, p=%s). %s" % (
            _e2["kontrast"], _e2["n_model"], _e2["iyi_ort_puan"], _e2["iyi_pozitif"], _e2["iyi_p"], _e2["kotu_ort_puan"], _e2["kotu_pozitif"], _e2["kotu_p"], _e2["not_"]))
    if _sb2.get("koken_uyarisi"):
        L.append("  ⚠️ köken: %s" % _sb2["koken_uyarisi"])


# --- EK BLOKLARIN MARKDOWN CIKTISI (155, 17.10.2026) ---
if K.get("ayristirma_kolu"):
    _ak = K["ayristirma_kolu"]; _v = _ak["varyans_ayrisimi"]; _ko = _ak["korelasyon"]
    L.append("\n## Ayristirma kolu (parti-eslenmis, 30 tohum) · EK-82\n")
    L.append("- %s" % _ak["tanim"])
    L.append("- n=**%d** · ort **%.2f** · ss **%.2f** · medyan %.2f · aralik %.2f--%.2f" % (
        _ak["n"], _ak["ort"], _ak["ss"], _ak["medyan"], _ak["min"], _ak["maks"]))
    _s = _ak["sampiyon"]; _o = _ak["sampiyon_disi_29"]
    L.append("- **sampiyon** (tohum 0) genel **%.4f** sira **%d/%d** · malign %.4f sira **%d/%d** · benign %.4f sira **%d/%d**" % (
        _s["deger"], _s["sira_genel"], _ak["n"], _s["malign"], _s["sira_malign"], _ak["n"], _s["benign"], _s["sira_benign"], _ak["n"]))
    L.append("- sampiyon disi 29 tohum: ort %.2f · ss %.2f · maks %.2f · **z=%+.2f** · ustunde kosum **%d**" % (
        _o["ort"], _o["ss"], _o["maks"], _o["z_sampiyon"], _o["ustunde_kosum"]))
    L.append("- sinif: malign **%.2f ± %.2f** · benign **%.2f ± %.2f**" % (
        _ak["sinif"]["malign_ort"], _ak["sinif"]["malign_ss"], _ak["sinif"]["benign_ort"], _ak["sinif"]["benign_ss"]))
    L.append("- **varyans ayrisimi** (%s): Var(mal) %.2f · Var(ben) %.2f · Cov %.2f -> hesap **%.4f** / olculen **%.4f** · kimlik kapandi: **%s**" % (
        _v["kimlik"], _v["var_malign"], _v["var_benign"], _v["kovaryans"], _v["var_genel_hesaplanan"], _v["var_genel_olculen"], _v["kimlik_kapandi"]))
    L.append("  paylar: benign **%%%.2f** · malign %%%.2f · kovaryans %%%.2f" % (
        _v["pay_benign_yuzde"], _v["pay_malign_yuzde"], _v["pay_kovaryans_yuzde"]))
    L.append("- **korelasyon** (birim **%s**, n=**%d**): Pearson genel-benign %+.3f · genel-malign %+.3f · Spearman genel-benign **%+.3f** · genel-malign **%+.3f**" % (
        _ko["birim"], _ko["n"], _ko["pearson_genel_benign"], _ko["pearson_genel_malign"], _ko["spearman_genel_benign"], _ko["spearman_genel_malign"]))
    L.append("  ⚠️ %s" % _ko["not_"])
    L.append("- **sira ortusmesi**: " + " · ".join("en iyi %s -> benign %d, malign %d" % (
        k.split("_")[-1], v["genel_kesisim_benign"], v["genel_kesisim_malign"]) for k, v in _ak["sira_ortusmesi"].items()))
    L.append("  ⓘ %s" % _ak["not_"])
if K.get("capraz_makine"):
    _c = K["capraz_makine"]
    L.append("\n## Capraz makine yeniden uretilebilirlik · EK-85\n")
    L.append("- %s" % _c["tanim"])
    L.append("- dnnlab3 **%.6f** ↔ 155 **%.6f** · fark **%+.2f puan** (malign %+.2f · benign %+.2f)" % (
        _c["dnnlab3_mAP50"], _c["mak155_mAP50"], _c["fark_puan"], _c["malign_fark_puan"], _c["benign_fark_puan"]))
    L.append("- tensor: ayni makine **%s** · capraz makine **%s**" % (_c["tensor_ayni_ayni_makine"], _c["tensor_ayni_capraz_makine"]))
    L.append("  ⚠️ eksen ayristirilabilir mi: **%s** — %s" % (_c["eksen_ayristirilabilir_mi"], _c["eksen_notu"]))
    L.append("  ⚠️ n_yineleme=**%d** · %s" % (_c["n_yineleme"], _c["not_"]))
if K.get("cozulen_optimizer"):
    _co = K["cozulen_optimizer"]; _m = _co["momentum_sapmasi"]
    L.append("\n## Cozulen optimizer denetimi (504 hucre) · EK-80\n")
    L.append("- istenen: %s" % _co["istenen"])
    L.append("- cozulen: %s" % _co["cozulen"])
    L.append("- `auto` yazan hucrelerin epok dagilimi: %s" % _co["auto_hucre_epok_dagilimi"])
    L.append("- **momentum sapmasi**: %d hucrede beyan **%s** degil **%s** — %s" % (
        _m["n_hucre"], _m["beyan"], _m["gercek"], _m["gerekce"]))
    L.append("  ⓘ %s" % _co["not_"])

if K.get("belirlenimcilik"):
    _bd = K["belirlenimcilik"]; _ba = _bd["bayt_aynilik"]
    L.append("\n## Belirlenimcilik ve sampiyon cifti · EK-81/EK-83\n")
    L.append("- %s" % _bd["tanim"])
    L.append("- sampiyon (yeniden olculen) **%.4f** ↔ Kohort B seed00 **%.4f** · fark **%+.2f puan**" % (
        _bd["sampiyon_yeniden_olculen"], _bd["kohortB_seed00"], _bd["cift_farki_puan"]))
    _kd = _bd["kohortB_dagilimi"]
    L.append("- Kohort B dagilimi: n=%d · ort %.2f · ss %.2f · maks %.2f  (%s)" % (
        _kd["n"], _kd["ort"], _kd["ss"], _kd["maks"], _kd["not_"]))
    L.append("- **bayt-aynilik: %s** (gozlenen %d kosum, ayni %d, ayrisik %d) · tensor ayni makine **%s** · capraz makine **%s**" % (
        _ba["oran"], _ba["gozlenen_kosum"], _ba["ayni"], _ba["ayrisik"], _ba["tensor_ayni_makine"], _ba["tensor_capraz_makine"]))
    L.append("  ⚠️ %s" % _ba["not_"])
    L.append("- **dislanan adaylar (%d)** — H87 denetimi: %s" % (len(_bd["dislanan_adaylar"]), _bd["h87_denetimi"]))
    for _a in _bd["dislanan_adaylar"]:
        L.append("  - `%s` → %s  *(%s)*" % (_a["aday"], _a["gerekce"], _a["gerekce_turu"]))
    L.append("- kalan aciklama: **%s**" % _bd["kalan_aciklama"])
    L.append("  ⓘ %s" % _bd["not_"])

L.append("\n## Kaynak dosyalar\n")
for k,v in K["_kaynaklar"].items():
    _d = v.get("depo_yolu") or v["yol"]
    _ok = "depodan dogrulanabilir" if v.get("depodan_dogrulanabilir") else ("DEPO BLOB FARKLI: %s" % v.get("depo_blob_md5") if v.get("depo_blob_md5") else "depoda izlenmiyor")
    L.append("- `%s` — md5 `%s` — %s"%(_d,v["md5"],_ok))
L.append("\n**Izlenebilirlik:** %s"%K["_izlenebilirlik"]["ozet"])
open(os.path.join(OUT,"KANONIK.md"),"w").write("\n".join(L)+"\n")
print("uretildi: KANONIK.md + KANONIK.json  (%d ark · %d esli · %d rejim)"%(
    len(K["arklar"]),len(K["esli"]),len(K["rejim_etkisi"])))
