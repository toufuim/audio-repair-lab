#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo '請先安裝 uv：https://docs.astral.sh/uv/getting-started/installation/'
  exit 1
fi
if [[ "$(uname -s)" == Darwin ]]; then
  LAB_ENV="${AUDIO_LAB_ENV:-$HOME/Library/Application Support/AudioRepairLab/qwen-venv}"
else
  LAB_ENV="${AUDIO_LAB_ENV:-$HOME/.local/share/audio-repair-lab/venv}"
fi
if [[ ! -x "$LAB_ENV/bin/python" ]]; then uv venv --python 3.12 "$LAB_ENV"; fi
uv pip install --python "$LAB_ENV/bin/python" -r requirements.txt
"$LAB_ENV/bin/python" -m scripts.download_models
echo '安裝完成，執行 bash start.sh 開啟本機網頁。'
