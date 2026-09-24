#!/bin/bash
set -e
cd "$(dirname "$0")"
URL='http://127.0.0.1:8765/'
if /usr/bin/curl -fsS --max-time 2 "${URL}api/health" 2>/dev/null | /usr/bin/grep -q '"status":"ok".*"model":"Qwen/'; then
  if [[ "${AUDIO_LAB_NO_BROWSER:-0}" != 1 ]]; then /usr/bin/open "$URL"; fi
  exit 0
fi
exec /bin/bash start.sh "$@"
