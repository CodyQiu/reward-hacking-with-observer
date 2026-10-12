#!/bin/bash
# One-time FarmShare setup, run from the repo root on a login node:
#   bash scripts/farmshare/setup.sh
# Builds .venv with the laptop's exact package versions (Python 3.12.13; CPU torch).
set -euo pipefail
UV=${UV:-$HOME/.local/bin/uv}
$UV python install 3.12.13
$UV venv --python 3.12.13 .venv
$UV pip install --python .venv/bin/python torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
$UV pip install --python .venv/bin/python -r scripts/farmshare/requirements.txt
.venv/bin/python -c "import jax, sbx, gymnasium, Box2D, torch; print('ok', jax.__version__, jax.devices())"
