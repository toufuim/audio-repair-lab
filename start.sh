#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" == Darwin ]]; then
  LAB_ENV="${AUDIO_LAB_ENV:-$HOME/Library/Application Support/AudioRepairLab/qwen-venv}"
else
  LAB_ENV="${AUDIO_LAB_ENV:-$HOME/.local/share/audio-repair-lab/venv}"
fi
if [[ ! -x "$LAB_ENV/bin/python" ]]; then echo '請先執行 bash install.sh'; exit 1; fi
exec "$LAB_ENV/bin/python" -m scripts.run "$@"
