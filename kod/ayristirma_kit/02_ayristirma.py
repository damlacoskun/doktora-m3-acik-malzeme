"""Ayristirma kosumu — sampiyonun COZULMUS yapilandirmasiyla 30 tohum, sampiyonun makinesinde.

Kohort B'yi ureten seed_sweep_9c.py'den TUREVDIR; yalnizca beyan edilen alan degisir.

SAMPIYONUN KIMLIGI (kanonik kayittan, 13.10.2026 denetimi):
  kanonik/_910_EK6_504_sinif_bazli_20260910.csv · YOLOv9-c/640/1000 · mAP50 0.800953
  agirlik: .../dnnlab3/yolov12_sgd_dnnlab3/runs/detect/9c/train_yolov9c_1000_epochs_640/weights/best.pt
  -> sampiyon dnnlab3'te, ACIKCA SGD yazilarak egitilmistir (910'un '_AdamW' adli kosumu
     kanonik izgaraya HIC girmemistir; 504 hucrede 'AdamW' gecen tek yol yoktur).

  COZULMUS degerler (args.yaml + results.csv lr izi + ckpt train_args):
    optimizer SGD · lr0 0.01 · momentum 0.937 · warmup_bias_lr 0.0
    batch: args.yaml '-1' yazar, ckpt train_args COZULMUS '8' tasir (mozaik nb=11 ile de dogrulandi)
    ilk epok lr/pg0 = 0.01*(11-1)/100 = 0.001  (kayitta 0.001)
    son epok lr/pg0 = 0.01*((1-999/1000)*0.99+0.01) = 1.099e-04 (kayitta 0.0001099)
    ultralytics 8.3.63 · python 3.9.25 · torch 2.2.2+cu118

AYRISTIRILACAK EKSEN = PARTI BOYUTU.
  Kohort B de ayni makinede, ayni SGD ile kosmustur; tek yapisal fark partinin
  AutoBatch'e birakilmasidir: 30 tohumun 23'u parti 6, altisi 7, yalnız biri (seed00) 8'e
  cozulmustur (iki bagimsiz yontemle dogrulandi: ckpt train_args ve gec-epok mozaik indisi
  990*nb; 30/30 ortusme). Sampiyon ise 8'e cozulmustur. Dolayisiyla "sampiyon kendi
  kohortunda 0/30" bulgusu tohum ile parti eksenini birlikte tasir.
  Bu kol partiyi 8'e SABITLER; boylece kohort ile sampiyon parti ekseninde eslenir ve
  0/30 aciklığından parti payi dusulur.

IKINCIL KOL (adamw_b8) yalnizca 910'un auto->AdamW kosumunu yineler; kanonik izgaraya
girmedigi icin makalenin birincil iddiasiyla ilgisi yoktur, istege bagli tutulmustur.
"""
import os, sys, json, argparse, csv, time

if not os.path.isdir("ultralytics"):
    raise SystemExit("bu betik yolov12_sgd_dnnlab3 depo kokunden kosmalidir (ultralytics/ bulunamadi)")
sys.path.insert(0, os.getcwd())
from ultralytics.models.yolo.detect import DetectionTrainer

MODEL = "ultralytics/cfg/models/v9/yolov9c.yaml"
DATA  = "ultralytics/cfg/datasets/data_4_1.yaml"
EPOCHS, IMGSZ = 1000, 640

# Kohort B / sampiyon ile AYNI olan her sey; farklar yalnizca KOL sozlugunde.
TABAN = dict(model=MODEL, data=DATA, epochs=EPOCHS, imgsz=IMGSZ,
             device=0, workers=4, patience=0, seed=0, exist_ok=True)

KOLLAR = {
    # BIRINCIL: sampiyonun cozulmus yapilandirmasi. Kohort B'den tek fark: parti SABIT 8.
    "sgd_b8":   dict(optimizer="SGD",   lr0=0.01,     momentum=0.937, warmup_bias_lr=0.0, batch=8),
    # IKINCIL (istege bagli): 910'un auto->AdamW kosumunun cozulmus degerleri.
    "adamw_b8": dict(optimizer="AdamW", lr0=0.001667, momentum=0.9,   warmup_bias_lr=0.0, batch=8),
}

# Ankraj: parti 8 (nb=11) icin ilk-epok lr/pg0 = lr0*(nb-1)/100.
BEKLENEN_ILK_LR = {"sgd_b8": 0.01*10/100, "adamw_b8": 0.001667*10/100}
TOLERANS = 1e-7


def ilk_epok_lr(kayit_dizini):
    with open(os.path.join(kayit_dizini, "results.csv")) as f:
        satir = next(csv.DictReader(f))
    return float(satir[[k for k in satir if k.strip() == "lr/pg0"][0]])


def cozulmus_parti(kayit_dizini):
    """ckpt train_args COZULMUS partiyi tasir; args.yaml tasimaz."""
    import torch
    c = torch.load(os.path.join(kayit_dizini, "weights", "best.pt"),
                   map_location="cpu", weights_only=False)
    return (c.get("train_args") or {}).get("batch"), c.get("version")


def ankraj_denetimi(kol, kayit_dizini, durdur=True):
    """H40: hesap kullanilmadan ONCE dogrulanir. H73: beklenen deger gercek sayidan gelir."""
    beklenen = BEKLENEN_ILK_LR[kol]
    olculen = ilk_epok_lr(kayit_dizini)
    parti, surum = cozulmus_parti(kayit_dizini)
    print(f"  [ankraj] ilk-epok lr/pg0 beklenen {beklenen:.7f} · olculen {olculen:.7f} "
          f"· sapma {abs(olculen-beklenen):.2e}")
    print(f"  [ankraj] cozulmus parti {parti} (beklenen 8) · ultralytics {surum} (beklenen 8.3.63)")
    hatalar = []
    if abs(olculen - beklenen) > TOLERANS: hatalar.append(f"ilk-epok lr {olculen} != {beklenen}")
    if parti != 8:                        hatalar.append(f"cozulmus parti {parti} != 8")
    if surum != "8.3.63":                 hatalar.append(f"ultralytics {surum} != 8.3.63")
    if hatalar:
        ileti = "ANKRAJ BASARISIZ: " + "; ".join(hatalar)
        if durdur: raise SystemExit(ileti + "  -> supurme DURDURULDU (30 saat bosa harcanmasin)")
        print("  [ankraj] UYARI: " + ileti)
    else:
        print("  [ankraj] TAMAM")
    return dict(ilk_epok_lr=olculen, beklenen_ilk_lr=beklenen,
                cozulmus_parti=parti, ultralytics=surum)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--kol", default="sgd_b8", choices=list(KOLLAR))
    a.add_argument("--tohum-bas", type=int, default=0)
    a.add_argument("--tohum-son", type=int, default=29)
    a.add_argument("--epochs", type=int, default=EPOCHS, help="duman testi icin (normalde 1000)")
    a.add_argument("--proje", default=None)
    g = a.parse_args()

    proje = g.proje or f"runs/detect/9c_ayristirma_{g.kol}"
    fark = KOLLAR[g.kol]
    print(f"=== AYRISTIRMA KOSUMU · kol={g.kol} · tohum {g.tohum_bas}-{g.tohum_son} · epochs={g.epochs}")
    print(f"=== bu kolun yapilandirmasi: {fark}")
    print(f"=== Kohort B ile ayni olan her sey: {TABAN}")

    os.makedirs(proje, exist_ok=True)
    with open(os.path.join(proje, "BEYAN.json"), "w") as f:
        json.dump(dict(kol=g.kol, yapilandirma=fark, taban=TABAN, epochs=g.epochs,
                       turetildigi_betik="seed_sweep_9c.py",
                       sampiyon=dict(yol="runs/detect/9c/train_yolov9c_1000_epochs_640",
                                     mAP50=0.800953, optimizer="SGD", cozulmus_parti=8),
                       kohort_B=dict(optimizer="SGD", batch_istenen=-1,
                                     batch_cozulen={"8": 1, "7": 6, "6": 23}),
                       beklenen_ilk_epok_lr=BEKLENEN_ILK_LR[g.kol]), f, indent=2, ensure_ascii=False)

    for tohum in range(g.tohum_bas, g.tohum_son + 1):
        ad = f"seed{tohum:02d}"
        kayit = os.path.join(proje, ad)
        if os.path.exists(os.path.join(kayit, "weights", "best.pt")):
            print(f"[atla] {ad} zaten tamam"); continue
        print(f"[basla] {g.kol} tohum={tohum}  ({time.strftime('%d.%m %H:%M')})", flush=True)
        DetectionTrainer(overrides=dict(TABAN, **fark, seed=tohum, project=proje,
                                        name=ad, epochs=g.epochs)).train()
        bilgi = ankraj_denetimi(g.kol, kayit, durdur=(tohum == g.tohum_bas))
        with open(os.path.join(kayit, "PROVENANS.json"), "w") as f:
            json.dump(dict(kol=g.kol, tohum=tohum, yapilandirma=fark, ankraj=bilgi),
                      f, indent=2, ensure_ascii=False)
        print(f"[bitti] {g.kol} tohum={tohum}  ({time.strftime('%d.%m %H:%M')})", flush=True)
    print(f"{g.tohum_son - g.tohum_bas + 1} tohum tamamlandi · kol {g.kol}")


if __name__ == "__main__":
    main()
