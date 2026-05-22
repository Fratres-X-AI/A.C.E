#!/usr/bin/env bash
# Paste this on a fresh RunPod Linux pod — clones A.C.E and runs the smoke test.
set -euo pipefail

REPO_URL="${ACE_REPO:-https://github.com/FratresMedAI/A.C.E.git}"
INSTALL_DIR="${ACE_DIR:-$HOME/A.C.E}"

echo "[ace] Bootstrap RunPod test"
echo "[ace] Repo : $REPO_URL"
echo "[ace] Dir  : $INSTALL_DIR"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  echo "[ace] Repo exists — pulling latest main..."
  git -C "$INSTALL_DIR" pull --ff-only origin main || true
fi

cd "$INSTALL_DIR"
bash scripts/runpod_smoke.sh "$@"
