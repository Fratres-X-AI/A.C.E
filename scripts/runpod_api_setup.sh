#!/usr/bin/env bash
# Run external Llama/chat API through A.C.E containment (no GPU / no HF download).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${ACE_LLM_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "[ace] ERROR: Set ACE_LLM_API_KEY (your Llama API key)."
  exit 1
fi
if [[ -z "${ACE_LLM_API_BASE:-}" && -z "${ACE_LLM_API_URL:-}" ]]; then
  echo "[ace] ERROR: Set ACE_LLM_API_BASE (e.g. https://api.together.xyz/v1)"
  echo "       or ACE_LLM_API_URL for a full chat/completions endpoint."
  exit 1
fi

export ACE_LLM_MODEL="${ACE_LLM_MODEL:-meta-llama/Meta-Llama-3-8B-Instruct}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q -U pip
python -m pip install -q -e .

echo "[ace] Model: $ACE_LLM_MODEL"
echo "[ace] API config OK — starting containment demo..."
python examples/runpod_api_demo.py --backend auto "$@"
