# KANONİK SAYI KAYDI

**Üretim:** 2026-10-22 22:43 · **Üreten:** `URET_kanonik.py`

> 🔴 **Bu dosya ELLE DÜZENLENMEZ.** Deney ilerledikçe `python3 URET_kanonik.py` ile yeniden üretilir.
> Makalelerde kullanılan her sayı burada bulunmalıdır; bulunmuyorsa kullanılamaz.

## Ark özetleri (conf 0,001 · mAP@0,5 · %)

| Ark | n | ort | ss | %95 GA | min–maks | durum |
|---|---|---|---|---|---|---|
| `kazanan_252550` | 30 | **83.29** | **3.93** | 81.82–84.76 | 74.0–90.8 | TAM |
| `kazanan_333334` | 30 | **82.70** | **4.20** | 81.13–84.27 | 73.1–90.8 | TAM |
| `kazanan_map1` | 30 | **83.43** | **3.18** | 82.24–84.62 | 76.9–88.3 | TAM |
| `taban_252550` | 30 | **82.16** | **5.79** | 79.99–84.32 | 71.8–92.8 | TAM |
| `taban_333334` | 30 | **82.79** | **4.45** | 81.13–84.45 | 72.8–90.7 | TAM |
| `taban_map1` | 30 | **80.75** | **4.38** | 79.11–82.38 | 70.8–87.9 | TAM |

## Eşli karşılaştırmalar (puan)

| Karşılaştırma | n | fark | %95 GA | dz | Wilcoxon p |
|---|---|---|---|---|---|
| `kazanan_eksi_taban_map1` | 30 | **+2.68** | +0.60..+4.76 | 0.48 | 0.0083 |
| `252550_eksi_map1_kazanan` | 30 | **-0.14** | -1.45..+1.18 | -0.04 | 0.5165 |
| `333334_eksi_map1_kazanan` | 30 | **-0.72** | -2.35..+0.90 | -0.17 | 0.5306 |
| `252550_eksi_map1_taban` | 30 | **+1.41** | -1.03..+3.85 | 0.22 | 0.1981 |

## Rejim etkisi (üç rejim eşli)

| Konfig | n tohum | Friedman χ² | p | Levene p | ss oranı |
|---|---|---|---|---|---|
| kazanan | 30 | 1.34 | **0.5118** | **0.4031** | 1.32 |
| taban | 30 | 5.75 | **0.0565** | **0.1172** | 1.32 |

## Tekil zirve (92,9) sınaması

- toplam koşum: **90** · band ort **83.14** (ss 3.77) · band maks **90.80**
- 92,9'a ulaşan koşum: **0 / 90**
- z-skoru **+2.98** (map1 kolu, n=30) ⟵ TEZDE KULLANILAN
- z-skoru **+2.59** (90 koşumun tamamı) — farklı tanım, karıştırma

  ⚠️ z_map1 = 92,9'un KENDI rejiminin (map1, n=30) bandindaki konumu -> TEZDE KULLANILAN. z_tumu = 90 kosumun tamaminin bandindaki konumu. Metinde hangisi kullanildiysa ACIKCA yazilmali.

## 256-ızgara (ham koşum çıktısı — 768 model)

Kaynak: `C3TR_kanonik_768.csv` · dilim **conf 0.001 / iou 0.5**. ⚠️ Bu değerler **tezden türetilmemiştir**; ham koşum çıktısındandır.

| Rejim | n | ort | ss | min | maks | en iyi konfig |
|---|---|---|---|---|---|---|
| 252550 | 256 | **76.90** | 6.26 | 56.0 | **91.8** | `backbone_c3-c3-c3-tr_head_c3-tr-tr-c3` |
| 333334 | 256 | **76.94** | 6.07 | 57.3 | **93.7** | `backbone_c3-c3-c3-tr_head_tr-tr-tr-tr` |
| map1 | 256 | **77.92** | 6.03 | 61.2 | **92.9** | `backbone_c3-c3-c3-c3_head_tr-tr-c3-tr` |

  Tekil konfig değerleri `KANONIK.json` → `izgara.<rejim>.<konfig>` altında.

## Izgara doğrulaması (ham veri ↔ tez eki)

- karşılaştırılan hücre: **3072** · ayrışan: **0** ⇒ **BIR ONDALIK DUYARLIKTA ORTUSUYOR; ham duyarlikta sinanmadi**
- yön: `ek2.tex` burada **kaynak değil, sınama hedefidir**; kayıt ham veriden üretilir.

## Seçim körlüğü — doyma + best/last (v2)

**Doyma** (eğitim-tepe mAP@0,5; PLATO temiz havuz):

| aile·epok | n | ss | benzersiz | ort | >0,99 |
|---|---|---|---|---|---|
| `ultralytics_1000` | 128 | 0.002236 | 20 | 0.9944 | 95.3% |
| `ultralytics_3000` | 126 | 0.000000 | 1 | 0.9950 | 100.0% |
| `ultralytics_6000` | 139 | 0.000000 | 1 | 0.9950 | 100.0% |
| `v4_1000` | 4 | 0.022678 | 4 | 0.5620 | 0.0% |
| `v4_3000` | 4 | 0.009919 | 4 | 0.5929 | 0.0% |
| `v4_6000` | 4 | 0.009262 | 4 | 0.6039 | 0.0% |
| `v7_1000` | 24 | 0.216033 | 24 | 0.7749 | 12.5% |
| `v7_3000` | 24 | 0.079916 | 20 | 0.9628 | 62.5% |
| `v7_6000` | 24 | 0.007568 | 17 | 0.9940 | 95.8% |

  ⓘ ULTRALYTICS 3000 ve 6000 epok: ss=0,000000 tek deger 0,995 (tam sabit; secim olcutu ayirt edici degiskenlik tasimiyor); 1000 epok ~%95 >0,99. v7 6000'de yakinsiyor (~%96), v4 ayri dusuk aile (~0,60). COK KAYNAK: PLATO CSV + 910 disk-scan 420 hucre + 155 raw results.csv.

**best.pt vs last.pt** (n=261): ortanca **+0.139** puan · %52.5 lehte · Wilcoxon p=**0.0195**
  epok ortancaları: 1000→+0.751 · 3000→+0.000 · 6000→+0.000  (sönüm)

## Sınıf-bazlı (v2) · 504 hücre · 43 model

- **Sınıf asimetrisi:** 504/504 pozitif · ort **+47.2 puan** (malign>benign). malign(kotu) hep benign(iyi) ustunde. Tezde bolum3:293'te ZATEN VAR - TEYIT, yeni bulgu degil.
- **rho:** genel–iyi **+0.901** · genel–kötü **+0.456** · kötü–iyi +0.073 (p=0.100). kotu_iyi BAGIMSIZLIK DEGIL (fazla soylem; p=0,10 sifiri reddetmiyor ama bagimsizlik kaniti degil). Asil kontrast: genel-iyi(0,90) >> genel-kotu(0,46) => genel mAP siralamasi buyuk olcude BENIGN siralamasi.
- **Epok–sınıf etkisi (6000 eksi 1000 epok, model n=43):** iyi **+7.46** puan (38 poz, p=2.6e-08) · kötü **-1.49** puan (13 poz, p=0.029). MODEL duzeyi (n=43); hucre duzeyi (n=168) SOZDE-YINELEME (ayni model 4 cozunurlukte). Epok artinca BENIGN iyilesir, MALIGN geriler (ters etki).
  ⚠️ köken: mAP sutunlari ek6 yayimlanmis; K/D sutunlari 910 yeniden-olcum; v7 protokol karisik; 4 hucrede K/D belirsiz. mAP tabanli grafik guvenli.

## Ayristirma kolu (parti-eslenmis, 30 tohum) · EK-82

- sampiyonun cozulmus yapilandirmasi, toplu is boyutu 8'e SABIT, 30 tohum, Kohort B'nin makinesinde (dnnlab3)
- n=**30** · ort **69.60** · ss **3.75** · medyan 69.70 · aralik 63.46--79.90
- **sampiyon** (tohum 0) genel **79.9009** sira **1/30** · malign 89.1043 sira **26/30** · benign 70.6975 sira **1/30**
- sampiyon disi 29 tohum: ort 69.24 · ss 3.26 · maks 76.02 · **z=+3.27** · ustunde kosum **0**
- sinif: malign **91.52 ± 2.43** · benign **47.68 ± 7.14**
- **varyans ayrisimi** (Var(genel)=[Var(mal)+Var(ben)+2Cov]/4): Var(mal) 5.92 · Var(ben) 51.02 · Cov -0.35 -> hesap **14.0594** / olculen **14.0594** · kimlik kapandi: **True**
  paylar: benign **%90.72** · malign %10.52 · kovaryans %-1.24
- **korelasyon** (birim **kosum**, n=**30**): Pearson genel-benign +0.946 · genel-malign +0.305 · Spearman genel-benign **+0.910** · genel-malign **+0.408**
  ⚠️ BIRIM KOSUM (n=30). sinif_bazli.rho ise 504 HUCRE uzerinde; iki buyukluk ayridir, karsilastirilmaz.
- **sira ortusmesi**: en iyi 1 -> benign 1, malign 0 · en iyi 3 -> benign 3, malign 0 · en iyi 5 -> benign 5, malign 0
  ⓘ EK-82. Kanonik sinif_bazli.rho notu 504 hucre duzeyinde 'genel siralama buyuk olcude benign siralamasi' demisti; bu blok ayni olguyu 30 KOSUM duzeyinde niceler (varyans payi + sira ortusmesi). Yeni bulgu degil, nicelemedir.

## Capraz makine yeniden uretilebilirlik · EK-85

- ayni yapilandirma + ayni tohum + ayni kart modeli (RTX 2080 Ti) + ayni ultralytics 8.3.63 + BAYT-AYNI veri; fark yalniz fiziksel makine ve CUDA derlemesi (cu118 vs cu121)
- dnnlab3 **0.799009** ↔ 155 **0.702184** · fark **+9.68 puan** (malign -3.35 · benign +22.71)
- tensor: ayni makine **937/937** · capraz makine **162/937**
  ⚠️ eksen ayristirilabilir mi: **False** — makine ile CUDA derlemesi BIRLIKTE degisiyor; iki etken ayristirilamaz
  ⚠️ n_yineleme=**1** · EK-85. TEK yineleme: acikligin VARLIGI kurulur, BUYUKLUGU kurulmaz. Eslesen 162 tensor dejenere (donmus BN, sabit DFL cekirdegi, tamsayi sayaclar); ogrenilmis tensorde eslesme yok.

## Cozulen optimizer denetimi (504 hucre) · EK-80

- istenen: {'SGD': 174, 'auto': 124, 'yok': 206}
- cozulen: {'SGD': 255, 'COZULEMEDI': 249}
- `auto` yazan hucrelerin epok dagilimi: {'6000': 124}
- **momentum sapmasi**: 124 hucrede beyan **0.937** degil **0.9** — auto dali momentumu 0,9'a zorlar (ultralytics 8.3.63 trainer.py); beyan edilen 0,937 o hucrelerde kullanilmamistir
  ⓘ EK-80. optimizer:auto yazan hucrelerin TAMAMI 6000 epoktadir ve SGD'ye cozulur; 1000/3000 epokta auto YOKTUR.

## Belirlenimcilik ve sampiyon cifti · EK-81/EK-83

- YOLOv9-c 640/1000 hucresi: ayni yapilandirma + ayni tohum (0) + ayni makine (dnnlab3) + ayni surum (8.3.63) ile UC kosum
- sampiyon (yeniden olculen) **79.9009** ↔ Kohort B seed00 **68.5227** · fark **+11.38 puan**
- Kohort B dagilimi: n=30 · ort 68.88 · ss 4.88 · maks 75.30  (Kohort B toplu is boyutu AutoBatch'e birakilmis: 8/7/6 olarak 1/6/23 tohumda cozulmustur)
- **bayt-aynilik: 2/3** (gozlenen 3 kosum, ayni 2, ayrisik 1) · tensor ayni makine **937/937** · capraz makine **162/937**
  ⚠️ ORAN KESTIRILEMEZ: n=3. 'oran 2/3' oldugu gibi bildirilir, siklik iddiasi yapilmaz. n>=5 olcumu tamamlanmadi.
- **dislanan adaylar (7)** — H87 denetimi: yedi dislamanin yedisi POZITIF OLCUM; hicbiri 'bulamadim' turu yokluk cikarimi degil
  - `kayitli yapilandirma` → 92/92 alan ckpt train_args + args.yaml'dan okundu  *(pozitif_olcum)*
  - `cozulmus toplu is boyutu` → ckpt train_args.batch=8 ucunde de  *(pozitif_olcum)*
  - `AutoBatch bellek yoklamasi` → sampiyon da batch:-1 ile kostu; yeni kol sabit 8 ile kostu ve BAYT-AYNI cikti (karsit kosum)  *(pozitif_olcum)*
  - `egitim verisi` → labels.jpg md5 ortustu (c171c876)  *(pozitif_olcum)*
  - `baslangic agirliklari` → epok 1 dogrulama kayiplari ucunde ayni  *(pozitif_olcum)*
  - `karisik duyarlik (AMP)` → bit-ozdes dokuz ciftin args.yaml'inda amp:true okundu; sampiyon hucresiyle ayni  *(pozitif_olcum)*
  - `etiket onbellegi (labels.cache)` → iki mekanizma olculdu: dosya sirasi md5 ayni (48653e13e591) ve dataset kurulduktan sonra random/numpy/torch durumlari ayni  *(pozitif_olcum)*
- kalan aciklama: **calisma zamani nondeterminizmi; kok neden tekil bir isleme indirgenemedi**
  ⓘ EK-81 + EK-83. Cift farki, sampiyonun YENIDEN OLCULEN degeriyle (0,799009) hesaplanir; izgarada kayitli deger (0,801) ile hesaplanirsa 11,6 cikar ve bu ayrim metinde beyan edilmistir.

## Kaynak dosyalar

- `veri/_bandA_BIRLESIK_conf0001_20260814.csv` — md5 `a9e47bb08adc` — depodan dogrulanabilir
- `veri/C3TR_kanonik_768.csv` — md5 `60d6e325202f` — depodan dogrulanabilir
- `kanonik/_910_PLATO_KOHORT_HAM_20260910.csv` — md5 `d04bc23f9f35` — depodan dogrulanabilir
- `kanonik/_910_BEST_VS_LAST_20260910.csv` — md5 `eb25226cf50b` — depodan dogrulanabilir
- `kanonik/_910_EK6_504_sinif_bazli_20260910.csv` — md5 `f1c0c30abf1b` — depodan dogrulanabilir
- `veri/_ayristirma30_sgd_b8_155_20261015.csv` — md5 `1a3390dacebd` — depodan dogrulanabilir
- `veri/_capraz_makine_155_20261016.csv` — md5 `fa54a9ddded7` — depodan dogrulanabilir
- `veri/_504_cozulen_optimizer_155_20261013.csv` — md5 `995b5240a7ed` — depodan dogrulanabilir
- `veri/seed30_yolov9c_20260728.csv` — md5 `8cc5757296d0` — depodan dogrulanabilir
- `veri/seed30_yolov5s_surumkohortu_20260730.csv` — md5 `60fababd5b3a` — depodan dogrulanabilir
- `veri/_heldout_altkume_v3_910_20260910.csv` — md5 `dc0a09221ffb` — depodan dogrulanabilir
- `veri/_parametre_nc2_155_20261017.csv` — md5 `0809434ad7a3` — depodan dogrulanabilir
- `veri/_ikiz_egitim_155_20261017.csv` — md5 `95cb5e6c1f21` — depodan dogrulanabilir
- `veri/_sampiyon_seed00_yeniden_degerlendirme_155_20261013.csv` — md5 `afd827b8b8a7` — depodan dogrulanabilir

**Izlenebilirlik:** HASH'LENEBILIR KAYNAKLARIN TAMAMI (14/14) DEPODAN DOGRULANABILIR; 15 alan DEPO DISI gonderme tasiyor (bkz. izlenmeyen) -- siniflar: cagdas_kayit, depoda_ad_ile_anilan, kamuya_acik_ucuncu_taraf, kamuya_acik_veri_yapilandirmasi, turetilmis_veri_depoda
