#!/usr/bin/env bash
# Build the A.C.E sandbox worker image used by the Docker backend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${ACE_DOCKER_IMAGE:-ace-aegis-sandbox:local}"

cd "$ROOT"
echo "[ace] Building Docker sandbox image: $IMAGE"
docker build -f Dockerfile.sandbox -t "$IMAGE" .
echo "[ace] Done. Run: python examples/runpod_smoke.py --backend docker"
