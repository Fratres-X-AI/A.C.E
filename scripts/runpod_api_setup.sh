#!/usr/bin/env bash
# Run external Llama/chat API through A.C.E containment (no GPU / no HF download).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Hugging Face Inference Router defaults (see huggingface.co inference providers UI).
export ACE_LLM_API_BASE="${ACE_LLM_API_BASE:-https://router.huggingface.co/v1}"
export ACE_LLM_MODEL="${ACE_LLM_MODEL:-meta-llama/Llama-3.1-8B-Instruct:novita}"

if [[ -n "${HF_TOKEN:-}" ]]; then
  export ACE_LLM_API_KEY="${ACE_LLM_API_KEY:-$HF_TOKEN}"
fi
if [[ -n "${HUGGINGFACE_HUB_TOKEN:-}" && -z "${ACE_LLM_API_KEY:-}" ]]; then
  export ACE_LLM_API_KEY="$HUGGINGFACE_HUB_TOKEN"
fi

if [[ -z "${ACE_LLM_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "[ace] ERROR: Set HF_TOKEN=hf_... (your Hugging Face token with inference access)."
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q -U pip
python -m pip install -q -e .

echo "[ace] Model: $ACE_LLM_MODEL"
echo "[ace] API base: $ACE_LLM_API_BASE"
python scripts/api_verify.py
echo "[ace] Starting API + containment demo..."
python examples/runpod_api_demo.py --backend auto "$@"
