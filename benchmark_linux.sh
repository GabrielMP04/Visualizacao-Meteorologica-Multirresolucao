#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Execute ./instalar_linux.sh primeiro."
  exit 1
fi
exec .venv/bin/python main.py --benchmark --seconds 12 --no-vsync
