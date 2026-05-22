#!/usr/bin/env bash
# Run inside a RunPod Linux pod or locally with Docker. Installs deps + runs smoke test.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BACKEND="${1:-auto}"
if [[ "${1:-}" == "--backend" ]]; then
  BACKEND="${2:-auto}"
fi

echo "[ace] RunPod smoke setup in $ROOT"

in_container=false
if [[ -f /.dockerenv ]] || grep -qaE 'docker|containerd' /proc/1/cgroup 2>/dev/null; then
  in_container=true
  echo "[ace] Nested container detected (RunPod pod) — preferring Docker backend"
fi

use_docker=false
if [[ "$BACKEND" == "docker" ]]; then
  use_docker=true
elif [[ "$BACKEND" == "auto" ]] && [[ "$in_container" == "true" ]]; then
  use_docker=true
elif [[ "$BACKEND" == "auto" ]] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if ! command -v bwrap >/dev/null 2>&1; then
    use_docker=true
  fi
fi

if [[ "$use_docker" == "true" ]]; then
  echo "[ace] Using Docker backend — building sandbox image if needed..."
  bash scripts/build_sandbox_image.sh
else
  if ! command -v bwrap >/dev/null 2>&1; then
    echo "[ace] Installing bubblewrap..."
    if command -v apt-get >/dev/null 2>&1; then
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -qq
      apt-get install -y bubblewrap
    else
      echo "[ace] bubblewrap not found. Use Docker instead:"
      echo "      bash scripts/runpod_smoke.sh --backend docker"
      exit 1
    fi
  fi
fi

if [[ ! -d .venv ]]; then
  echo "[ace] Creating virtualenv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[ace] Installing A.C.E..."
python -m pip install -q -U pip
python -m pip install -q -e .

echo "[ace] Running smoke test..."
python examples/runpod_smoke.py "$@"
