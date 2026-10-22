#!/usr/bin/env bash
# Kohort B'nin ORTAMINI yeniden kurar. Hedef: Python 3.9.x + torch 2.2.2+cu118
# (kaynak: seed_sweep_9c.log satir 3 -> "Python-3.9.25 torch-2.2.2+cu118")
# Mevcut ortamlarin hicbiri bu degil; farkli torch ile kosmak yazilim eksenini kirletir.
set -euo pipefail
ENV=ayr39
C=$HOME/anaconda3
HEDEF_TORCH="2.2.2+cu118"
HEDEF_PY_MINOR="3.9"

if [ ! -x "$C/envs/$ENV/bin/python" ]; then
  "$C/bin/conda" create -y -n "$ENV" python=3.9
fi
P="$C/envs/$ENV/bin/python"
"$P" -m pip install -q --upgrade pip
"$P" -m pip install -q torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cu118
"$P" -m pip install -q huggingface_hub opencv-python-headless pandas pyyaml psutil tqdm matplotlib scipy requests py-cpuinfo ultralytics-thop pillow

# --- ANKRAJ: ortam hedefle birebir mi? Degilse DURDUR (uyarma, durdur).
"$P" - <<PY
import sys, torch
py = f"{sys.version_info.major}.{sys.version_info.minor}"
tv = torch.__version__
hatalar = []
if py != "$HEDEF_PY_MINOR": hatalar.append(f"python {py} != $HEDEF_PY_MINOR")
if tv != "$HEDEF_TORCH":    hatalar.append(f"torch {tv} != $HEDEF_TORCH")
if not torch.cuda.is_available(): hatalar.append("CUDA yok")
print(f"olculen: python {sys.version.split()[0]} · torch {tv} · cuda {torch.cuda.is_available()} · {torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-'}")
if hatalar:
    print("ORTAM ANKRAJI BASARISIZ: " + "; ".join(hatalar), file=sys.stderr); sys.exit(1)
print("ortam ankraji TAMAM — Kohort B ile ayni yazilim yigini")
PY
echo "ortam hazir: $P"
