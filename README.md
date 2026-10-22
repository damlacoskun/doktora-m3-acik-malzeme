# M3 — Açık Malzeme Arşivi

YOLOv3–v12 standart karşılaştırması ve tekrarlanabilirlik çalışmasının (M3) bütün nicel
sonuçlarının türetildiği **koşum kayıtları, kanonik üretici ve çözümleme betikleri**.

> Bu arşiv, makalenin "Veri ve kod erişilebilirliği" beyanının adresidir. Makalede geçen
> her sayı, buradaki kaynaklardan ve `kanonik/URET_kanonik.py` üreticisinden türetilmiştir.

## Yapı

```
veri/              11 kosum kaydi (CSV)
kanonik/           3 kosum kaydi (CSV) + kanonik uretici + uretilen kayit
  URET_kanonik.py    kaydi URETIR; KANONIK.json/md onun CIKTISIDIR
  KANONIK.json       makine-okunur kanonik kayit (30 ust duzey blok)
  KANONIK.md         ayni kaydin okunabilir bicimi
kod/               cozumleme ve ek-malzeme uretim betikleri
  mde.py                 MDE tablosu (scipy yok; t dagilimi bes bilinen degere ankrajli)
  uret_m3_ek_izgara.py   504 hucrelik izgara ekini kanonik CSV'den uretir
  uret_m3_ek_optimizer.py  cozulen optimizer ekini uretir
  ayristirma_kit/        ayristirma kolunun ortam + kosum + duman betikleri
DOGRULA.py         okura donuk butunluk dogrulamasi
```

## Doğrulama

```bash
python3 DOGRULA.py
```
**İki ayaklı:**

| ayak | kapsam | referans |
|---|---|---|
| **[1/2]** | 14 **veri kaynağı** | `kanonik/KANONIK.json` → `_kaynaklar[*].sha256` |
| **[2/2]** | **arşivin tamamı** (kod dosyaları dahil) | `MANIFEST.sha256` |

Çıkış `0` = ikisi de geçti, `1` = en az bir uyuşmazlık (hangi dosya olduğu basılır).
Manifestoda olmayan **fazla** bir dosya da uyuşmazlık sayılır.

**İkinci ayak neden var:** birinci ayak yalnız veri kaynaklarını kapsıyordu. Bir okur
`URET_kanonik.py`'yi ya da `kod/mde.py`'yi değiştirip yeniden koşsa farklı sayılar alır ve
doğrulama yine *"14/14 geçti"* derdi. (Bulgu: bağımsız denetim, 23.10.2026.) Sınandı:
`kod/mde.py` · `kanonik/URET_kanonik.py` · `kanonik/KANONIK.json` değişiklikleri ve arşive
eklenen yeni bir dosya — **dördü de çıkış 1** verdi; geri yüklendiğinde çıkış 0.

**KAPSAM DIŞI (beyan):** `MANIFEST.sha256` **kendi özetini içermez** — içerse özet kendini
değiştirirdi. Bu dosyanın bütünlüğü arşivin içinden doğrulanamaz; dışarıdan (depo işleme
kimliği ya da ayrı bir kopya ile) doğrulanması gerekir. Arşivin geri kalanının tamamı,
`KANONIK.json` dahil, kapsanır.

Manifesto bir **çıktıdır**, elle düzenlenmez: `python3 URET_MANIFESTO.py` ile üretilir.
`DOGRULA.py` onu yalnız **okur** — kendi referansını yeniden yazabilen bir doğrulayıcı,
doğrulayıcı değildir.

**Özet:** kanonik kayıt her kaynak için **tam sha256** (64 karakter) taşır; doğrulama
onunla yapılır. Kayıt ayrıca geriye dönük uyum için 12 karaktere kırpılmış bir md5 alanı da
tutar (`md5`), ama `DOGRULA.py` sha256'yı kullanır.

Kayıt özünde 22.10.2026'ya kadar yalnız kırpılmış md5 (48 bit) taşıyordu; bu, kazara
bozulmayı yakalar ama kasıtlı kurcalamaya zayıftır. Arşiv kamuya açılacağı için tam sha256
kanonik üreticiye eklendi ve kaydın Katman 0 geçidi altına alındı — yani `sha256` alanı da
elle düzenlenemez (tek karakteri değişse `--dogrula` kaynak depoda çıkış 1 verir).

## Kanonik kaydı yeniden üretmek

```bash
python3 kanonik/URET_kanonik.py            # KANONIK.json + KANONIK.md uretir
```

⚠️ **`--dogrula` kapısı bu arşivde GEÇMEZ ve bu beklenen davranıştır.** O kapı, kaydın
*kaynak depoya işlenen bayt dizisinden* (`git show HEAD:`) doğrulanmasını sınar; bu arşiv bir
git deposu değildir, dolayısıyla `depo_blob_md5` çözülemez ve `depodan_dogrulanabilir`
`False` olur. Ayrıca `yerel_yol.yol` alanı kaydı üreten makinenin mutlak yolunu taşır ve
arşivde farklıdır. Arşivde anlamlı doğrulama **`DOGRULA.py`**'dir.

Kaynak depoda `--dogrula` şunu güvence altına alır: *kayıt, üreticinin çıktısıyla özdeştir*
(oynak alan olarak yalnız `_uretim` damgası dışlanır, **sayısal tolerans yoktur**).

## Mimari kural — kayıt bir ÇIKTIDIR, asla girdi değil

`KANONIK.json` ve `KANONIK.md` **elle düzenlenmez**. Her ikisi de `URET_kanonik.py`
tarafından kaynak CSV'lerden üretilir. Makaledeki bir sayı değişecekse değişen şey kaynak
veri ya da üretici olmalıdır, kayıt değil. (Bu kural, çalışmanın kendi savının bir
sonucudur: tekil değerlerin yeniden üretilemediğini gösteren bir çalışma, kendi sayılarını
elle düzeltilebilir bir dosyada tutamaz.)

## İzlenebilirliğin kapsamı ve sınırı

Kanonik kayıttaki `_izlenebilirlik` bloğu, kayıttaki **bütün** kaynak göndermelerini tarar
ve depodan çözülemeyen her göndermeyi sınıfıyla birlikte listeler. Ölçülen durum:

- **14/14** hash'lenebilir kaynak kaynak depodan doğrulanabilir
- **15 alan** depo dışı gönderme taşır; sınıfları: `cagdas_kayit`,
  `depoda_ad_ile_anilan`, `kamuya_acik_ucuncu_taraf`, `kamuya_acik_veri_yapilandirmasi`,
  `turetilmis_veri_depoda`

Bu 15 alan **bu arşivde de yoktur** ve kayıt bunu kendi içinde beyan eder. Yani arşiv
"her şeyi içeriyor" demez; **neyi içermediğini de söyler**.

## Provenans kolonları

İki CSV (`veri/seed30_yolov9c_20260728.csv`, `kanonik/_910_EK6_504_sinif_bazli_20260910.csv`)
`weight_path` / `weight` kolonunda, satırı üreten ağırlık dosyasının üretildiği makinedeki
yolunu taşır. Bu yollar **okur tarafından erişilebilir değildir**; kaydın hangi koşumdan
geldiğini belgelemek için tutulmuştur.

## Kalıcılık sınırı

Bu arşiv bir git deposudur, **kalıcı kimlik (DOI) taşımaz**. Bir depo yeniden
adlandırılabilir, özele çekilebilir, zorla itilebilir ya da silinebilir. Dolayısıyla
yukarıdaki commit kimliği **değişmez bir gönderme değildir**; yalnız *bu* deponun *o*
anındaki durumunu adlandırır. Kalıcı kimlik gerekiyorsa arşivin bir veri havuzuna
yatırılması gerekir.

## Veri kümesi

Çalışma kamuya açık **INbreast** veri kümesini kullanmıştır. Veri kümesinin kendisi bu
arşivde **yoktur** (üçüncü taraf lisansı); arşivde yalnız o veriden üretilen koşum kayıtları
bulunur.
