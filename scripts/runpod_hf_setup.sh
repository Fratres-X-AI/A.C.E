#!/usr/bin/env bash
# Install HF stack on RunPod and run real-model containment demo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Default: Qwen2 0.5B — ungated, ~1GB download, no license form.
export ACE_HF_MODEL="${ACE_HF_MODEL:-Qwen/Qwen2-0.5B-Instruct}"
export ACE_HF_LOAD_4BIT="${ACE_HF_LOAD_4BIT:-0}"
export ACE_HF_MAX_NEW_TOKENS="${ACE_HF_MAX_NEW_TOKENS:-128}"

if [[ -n "${HF_TOKEN:-}" ]]; then
  export HUGGINGFACE_HUB_TOKEN="${HUGGINGFACE_HUB_TOKEN:-$HF_TOKEN}"
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q -U pip
python -m pip install -q -e ".[hf]"

echo "[ace] Model: $ACE_HF_MODEL (4bit=$ACE_HF_LOAD_4BIT)"
echo "[ace] Verifying Hugging Face access..."
python scripts/hf_verify.py

echo "[ace] Starting HF + containment demo..."
python examples/runpod_hf_demo.py --backend auto "$@"
