# A.C.E Integration Guide

## Ollama (Local)

```python
import requests
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.session import Session
from aegis.ifc.labels import PUBLIC

engine = ContainmentEngine()
session = Session()

def ollama_model(payload: dict) -> str:
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": payload["query"], "stream": False},
        timeout=120,
    )
    return resp.json()["response"]

result = engine.process(
    {"query": "Summarize public documentation"},
    session,
    ollama_model,
    input_label=PUBLIC,
    output_clearance=PUBLIC,
)
print(result.output)
```

## RunPod

### Basic handler wrapping

1. Deploy container with A.C.E installed (`pip install -e .`)
2. Wrap RunPod handler with `InstrumentedRunner`
3. Bind session to RunPod pod ID for audit correlation
4. Export compliance artifacts to object storage after each batch

```python
from aegis.execution.instrumented_runner import InstrumentedRunner
from aegis.audit.tamper_proof_log import TamperProofLog

log = TamperProofLog()
runner = InstrumentedRunner(audit_log=log)
output = runner.run(your_handler, {"input": "..."})
```

### RunPod integrated (v0.2.0)

Deploy A.C.E inside a RunPod pod with Docker enabled for real sandbox isolation:

```python
from aegis.core.containment_engine import ContainmentEngine
from aegis.core.policy import Policy
from aegis.core.session import Session
from aegis.ifc.labels import INTERNAL, PUBLIC
from aegis.sandbox.manager import SandboxManager
from aegis.tunnel.providers import generate_cloudflare_config
from aegis.tunnel.simulated_tunnel import SimulatedTunnel

policy = Policy.from_file("policy.yaml")
engine = ContainmentEngine(policy=policy)
session = Session()
session.issue_capability("runpod-inference")

sandbox = SandboxManager(policy.policy.sandbox).create_sandbox()
tunnel = SimulatedTunnel(config=policy.policy.tunnel)

result = engine.process_integrated(
    {"query": "summarize"},
    session,
    your_vllm_handler,
    sandbox=sandbox,
    tunnel=tunnel,
    input_label=INTERNAL,
    output_clearance=PUBLIC,
)

# Optional: expose via Cloudflare Tunnel manifest
manifest = generate_cloudflare_config(
    "ace-runpod",
    "inference.yourdomain.com",
    service_url="http://localhost:8080",
)
```

For production, replace `SimulatedTunnel` with a Cloudflare or WireGuard deployment using configs from `aegis.tunnel.providers`.

## TEE Integration

A.C.E ships first-class Intel TDX and AMD SEV-SNP adapters with auto-detection.

### Quick start

```python
from aegis.execution.tee_factory import create_tee_environment, detect_platform
from aegis.core.session import Session

platform = detect_platform()  # intel-tdx | amd-sev-snp | simulated
session = Session(tee=create_tee_environment(platform))
quote = session.bind_tee("my-nonce")
print(quote.tee_type, quote.hardware_backed, quote.measurement)
```

Run the demo:

```bash
python examples/tee_attestation_demo.py
```

### Platform detection order

| Priority | Intel TDX | AMD SEV-SNP |
|----------|-----------|-------------|
| 1 | `/dev/tdx_guest` ioctl | `/dev/sev-guest` ioctl |
| 2 | `INTEL_TDX_QUOTE_PATH` env | `AMD_SEV_SNP_QUOTE_PATH` env |
| 3 | Azure IMDS `/attestation/TDX` | `/sys/firmware/sev-guest/id` sysfs |
| 4 | `/sys/firmware/tdx_guest/status` | — |
| 5 | Simulated fallback (dev) | Simulated fallback (dev) |

Force a platform with `ACE_TEE_PLATFORM=intel-tdx|amd-sev-snp|simulated`.

### Deploying on confidential VMs

**Azure Confidential VM (TDX):** Attestation is fetched automatically via IMDS when running inside the guest. Set `ACE_DISABLE_AZURE_IMDS=1` to skip in air-gapped environments.

**AMD SEV-SNP on Linux:** Ensure `sev-guest` module is loaded and `/dev/sev-guest` is accessible. Pre-export reports to a file and set `AMD_SEV_SNP_QUOTE_PATH=/run/aegis/guest.report` when using a sidecar attestation agent.

**Intel TDX on Linux:** Requires `tdx-guest` driver (Linux 6.8+). Alternatively inject quotes via `INTEL_TDX_QUOTE_PATH`.

### Production verification (next step)

Replace `verify_attestation_stub()` with:

| Platform | Verifier |
|----------|----------|
| Intel TDX | Intel DCAP QVL, Azure Attestation SDK |
| AMD SEV-SNP | AMD KDS/VCEK chain via `sev-tool` |
| Azure | `az attestation` policy validation |

```python
from aegis.execution.tee_abstraction import verify_attestation_stub

# Stub today — swap for DCAP/KDS in production
assert verify_attestation_stub(session.attestation)
```

### Legacy manual integration

Implement the `TEEEnvironment` protocol for other platforms:

| Platform | SDK | Notes |
|----------|-----|-------|
| NVIDIA CC | Confidential Computing | GPU memory encryption |
| AWS Nitro | Nitro Enclaves | Enclave image hash |

## Compliance Artifact Export

```python
from aegis.audit.metrics import ContainmentMetrics

metrics = ContainmentMetrics()
# ... after benchmark run ...
metrics.export_compliance_artifact("compliance_metrics.json")
```

Include tamper-evident log export:

```python
events = engine.audit_log.export_events(dp_epsilon=1.0)  # optional DP
```

## Policy-as-Code

Create `policy.yaml`:

```yaml
policy:
  default_sensitivity: INTERNAL
  fail_closed: true
  allow_declassification: false
  guardian:
    max_entropy_bits_per_char: 5.5
    max_output_bytes_per_minute: 50000
    canary_detection_enabled: true
```

Load at runtime:

```python
from aegis.core.policy import Policy
from aegis.core.containment_engine import ContainmentEngine

engine = ContainmentEngine(policy=Policy.from_file("policy.yaml"))
```
