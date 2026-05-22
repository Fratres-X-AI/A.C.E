#!/usr/bin/env bash
# Install HF stack on RunPod and run real-model containment demo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${HF_TOKEN:-}" && -z "${HUGGINGFACE_HUB_TOKEN:-}" ]]; then
  echo "[ace] ERROR: export HF_TOKEN=hf_... before running"
  exit 1
fi

# Default: small instruct model (~1.5GB). Override with ACE_HF_MODEL if needed.
export ACE_HF_MODEL="${ACE_HF_MODEL:-meta-llama/Llama-3.2-1B-Instruct}"
export ACE_HF_LOAD_4BIT="${ACE_HF_LOAD_4BIT:-0}"
export ACE_HF_MAX_NEW_TOKENS="${ACE_HF_MAX_NEW_TOKENS:-128}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q -U pip
python -m pip install -q -e ".[hf]"

echo "[ace] Model: $ACE_HF_MODEL (4bit=$ACE_HF_LOAD_4BIT)"
echo "[ace] Starting HF + containment demo..."
python examples/runpod_hf_demo.py --backend auto "$@"
