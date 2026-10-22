#!/usr/bin/env bash
# 30 saatlik supurmeden ONCE 3 epokluk duman testi: ankraj gercekten atesliyor mu?
# H73: beklenen deger gercek sayidan hesaplanir ve vaka yazilmadan ONCE basilir.
set -euo pipefail
R=$HOME/Desktop/damla/yolov12_sgd_dnnlab3
P=$HOME/anaconda3/envs/ayr39/bin/python
cd "$R"
echo "=== DUMAN: sgd_b8 · 3 epok · tek tohum (ankrajin ilk-epok lr'si 3 epokta da ayni)"
"$P" "$HOME/Desktop/damla/_AYRISTIRMA_kit_155/02_ayristirma.py" \
  --kol sgd_b8 --tohum-bas 0 --tohum-son 0 --epochs 3 \
  --proje runs/detect/_duman_ayristirma
echo "=== DUMAN TAMAM — ankraj gecti. Supurme baslatilabilir."
