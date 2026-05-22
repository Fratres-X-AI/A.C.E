# RunPod Quickstart (60 seconds)

Test A.C.E sandbox backends on a **Linux RunPod pod** or **locally with Docker**.

## Docker (easiest if Docker is already running)

From the repo root:

```bash
docker build -f Dockerfile.sandbox -t ace-aegis-sandbox:local .
python examples/runpod_smoke.py --backend docker
```

Or one script (Git Bash / RunPod):

```bash
bash scripts/runpod_smoke.sh --backend docker
```

That builds the `ace-aegis-sandbox:local` image (A.C.E + worker pre-installed) and runs the full integrated smoke test.

## RunPod GPU pods (nested containers)

RunPod pods **cannot create Linux namespaces** (bubblewrap fails) and usually have **no Docker**.

Use **`auto`** (picks the `process` backend — separate worker subprocess) or explicitly:

```bash
cd ~/A.C.E && git pull && bash scripts/runpod_smoke.sh --backend auto
# or
bash scripts/runpod_smoke.sh --backend process
```

The `process` backend runs `python -m aegis.sandbox._worker` in a **separate OS process** with full IFC/guardians/audit. It does not use namespace isolation (RunPod limitation). For full isolation, deploy on a bare-metal VM with bubblewrap.

## Real Hugging Face model (small default)

Uses **Qwen2-0.5B-Instruct** by default (~1GB, ungated — no license form). Model loads once on GPU; containment runs through the `process` backend.

```bash
cd ~/A.C.E && git pull
bash scripts/runpod_hf_setup.sh
```

For gated models (Llama, etc.) pass your token **and** accept the model license on huggingface.co:

```bash
export HF_TOKEN=hf_your_token_here
export ACE_HF_MODEL=meta-llama/Llama-3.2-1B-Instruct
bash scripts/runpod_hf_setup.sh
```

First run downloads weights and installs PyTorch — allow a few minutes.

## Hugging Face Inference API — Llama (no GPU, no weight download)

Uses the [HF Inference Router](https://huggingface.co/docs/inference-providers) — same as the "Inference Providers" UI on the model page. Your existing `HF_TOKEN` is the API key.

```bash
cd ~/A.C.E && git pull
export HF_TOKEN=hf_your_token_here
bash scripts/runpod_api_setup.sh
```

Defaults: `meta-llama/Llama-3.1-8B-Instruct:novita` via `https://router.huggingface.co/v1`.

Change provider by setting the model suffix (e.g. `:cerebras`, `:nscale`) or pick **Fastest** routing in the HF UI and copy the model string:

```bash
export ACE_LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct:cerebras
bash scripts/runpod_api_setup.sh
```

Other OpenAI-compatible providers (Together, Groq, etc.) still work via `ACE_LLM_API_BASE` + `ACE_LLM_API_KEY`.

## Already cloned?

```bash
cd ~/A.C.E   # or your clone path
bash scripts/runpod_smoke.sh
```

## Pick a backend

```bash
bash scripts/runpod_smoke.sh --backend auto        # bubblewrap on Linux (default)
bash scripts/runpod_smoke.sh --backend bubblewrap
bash scripts/runpod_smoke.sh --backend docker      # if Docker is running on the pod
```

Full demo with all layers:

```bash
source .venv/bin/activate
python examples/sandbox_backend_demo.py --backend auto
python examples/integrated_sandbox_tunnel_demo.py
```

## RunPod pod requirements

| Requirement | Why |
|-------------|-----|
| **Linux pod** | bubblewrap / gVisor / Firecracker are Linux-only |
| **SSH or web terminal** | Serverless workers are not ideal for namespace sandboxes |
| **Ubuntu/Debian** | `runpod_smoke.sh` auto-installs bubblewrap via `apt` |
| **~2 GB disk** | venv + repo |

**Recommended:** Standard GPU or CPU pod template (PyTorch/Ubuntu). Privileged pods are not required for bubblewrap when running as root (common on RunPod).

## Backend choice on RunPod

| Backend | Effort | When to use |
|---------|--------|-------------|
| **bubblewrap** | Easiest — one `apt install` | Default; daily dev and smoke tests |
| **docker** | Medium — Docker daemon on pod | Fallback if bwrap unavailable |
| **gvisor** | Hard — install `runsc` + rootfs | Stronger syscall isolation |
| **firecracker** | Hardest — kernel + rootfs images | MicroVM production; set `ACE_FC_KERNEL` and `ACE_FC_ROOTFS` |

Set explicitly:

```bash
export ACE_SANDBOX_BACKEND=bubblewrap
# or in policy.yaml: sandbox.backend: bubblewrap
```

## Wire your own model

After smoke test passes, wrap your vLLM/Ollama handler:

```python
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.ifc.labels import INTERNAL, PUBLIC

policy = Policy.from_file("policy.yaml")
engine = ContainmentEngine(policy=policy)
session = Session()
session.issue_capability("runpod-inference")
session.sandbox_backend = "auto"

result = engine.process_integrated(
    {"query": "your prompt"},
    session,
    your_model_fn,
    sandbox_backend="auto",
    input_label=INTERNAL,
    output_clearance=PUBLIC,
)
print(result.output)
```

See also [`integration_guide.md`](integration_guide.md).

## Troubleshooting

**No sandbox backend available**

```bash
sudo apt-get update && sudo apt-get install -y bubblewrap
which bwrap && bwrap --version
bash scripts/runpod_smoke.sh
```

**Docker fallback**

```bash
docker info   # must succeed
bash scripts/runpod_smoke.sh --backend docker
```

**Smoke test blocked (guardian)**

The mock workload should pass with `PUBLIC` labels. If blocked, check `policy.yaml` guardian thresholds or run with verbose audit:

```bash
python examples/runpod_smoke.py --backend auto
```
