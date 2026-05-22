"""Hugging Face inference runtime — load once, serve over loopback HTTP."""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger(__name__)

# Ungated, tiny, fast — no Meta license click-through required.
_DEFAULT_MODEL = "Qwen/Qwen2-0.5B-Instruct"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_server_started = False
_server_lock = threading.Lock()
_model_bundle: dict[str, Any] | None = None


def hf_model_id() -> str:
    return os.environ.get("ACE_HF_MODEL", _DEFAULT_MODEL)


def hf_token() -> str | None:
    raw = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if raw and raw.strip():
        return raw.strip()
    try:
        from huggingface_hub import get_token

        cached = get_token()
        if cached:
            return cached
    except ImportError:
        return None
    return None


def resolve_hf_token() -> str | None:
    """Token from env vars or ~/.cache/huggingface/token."""
    return hf_token()


def verify_hf_auth(model_id: str | None = None) -> dict[str, Any]:
    """Check token validity, HF username, and optional gated-model access."""
    from huggingface_hub import HfApi
    from huggingface_hub.utils import GatedRepoError, HfHubHTTPError

    target = model_id or hf_model_id()
    token = resolve_hf_token()
    api = HfApi()
    username: str | None = None

    if token:
        login_hf(persist=True)
        try:
            who = api.whoami(token=token)
        except HfHubHTTPError as exc:
            return {"ok": False, "error": f"HF token rejected: {exc}"}

        username = str(who.get("name") or who.get("fullname") or "?")
        expected = os.environ.get("HF_USERNAME")
        if expected and expected.lstrip("@").lower() != username.lower():
            return {
                "ok": False,
                "username": username,
                "error": (
                    f"HF_TOKEN belongs to @{username}, but HF_USERNAME=@{expected}. "
                    "Use a token from the account that accepted the model license."
                ),
            }

    try:
        api.model_info(target, token=token)
    except GatedRepoError:
        if not token:
            return {
                "ok": False,
                "error": (
                    f"{target!r} is gated. Export HF_TOKEN=hf_... from the account "
                    "that accepted the model license, then re-run."
                ),
            }
        return {
            "ok": False,
            "username": username,
            "error": (
                f"@{username} cannot access gated model {target!r}. "
                f"Open https://huggingface.co/{target} while logged in as "
                f"@{username} and click 'Agree and access repository'."
            ),
        }
    except HfHubHTTPError as exc:
        if username:
            return {
                "ok": False,
                "username": username,
                "error": f"Cannot reach {target!r} as @{username}: {exc}",
            }
        return {"ok": False, "error": f"Cannot reach {target!r}: {exc}"}

    result: dict[str, Any] = {"ok": True, "model": target}
    if username:
        result["username"] = username
    return result


def hf_server_url() -> str:
    host = os.environ.get("ACE_HF_SERVER_HOST", _DEFAULT_HOST)
    port = int(os.environ.get("ACE_HF_SERVER_PORT", str(_DEFAULT_PORT)))
    return f"http://{host}:{port}"


def _use_4bit() -> bool:
    return os.environ.get("ACE_HF_LOAD_4BIT", "0").lower() in {"1", "true", "yes"}


def _max_new_tokens() -> int:
    return int(os.environ.get("ACE_HF_MAX_NEW_TOKENS", "128"))


def _pretrained_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {"trust_remote_code": True}
    token = resolve_hf_token()
    if token:
        kwargs["token"] = token
    return kwargs


def login_hf(*, persist: bool = False) -> None:
    """Authenticate with HF hub when a token is present."""
    token = resolve_hf_token()
    if not token:
        logger.info("No HF token — public models only.")
        return
    from huggingface_hub import login

    login(token=token, add_to_git_credential=persist)
    if persist:
        os.environ.setdefault("HF_TOKEN", token)
        os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", token)


def load_model_bundle() -> dict[str, Any]:
    global _model_bundle  # noqa: PLW0603
    if _model_bundle is not None:
        return _model_bundle

    model_id = hf_model_id()
    check = verify_hf_auth(model_id)
    if not check.get("ok"):
        msg = str(check.get("error", "HF auth failed"))
        raise RuntimeError(msg)
    username = check.get("username")
    if username:
        logger.info("HF authenticated as @%s", username)

    login_hf(persist=True)
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    logger.info("Loading HF model: %s (4bit=%s)", model_id, _use_4bit())
    hub_kwargs = _pretrained_kwargs()

    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_id, **hub_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_kwargs: dict[str, Any] = {
        **hub_kwargs,
        "device_map": "auto",
    }
    if _use_4bit():
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
    else:
        load_kwargs["torch_dtype"] = torch.bfloat16

    model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
    _model_bundle = {"model": model, "tokenizer": tokenizer, "model_id": model_id}
    return _model_bundle


def generate_text(prompt: str, *, max_new_tokens: int | None = None) -> str:
    import torch

    bundle = load_model_bundle()
    model = bundle["model"]
    tokenizer = bundle["tokenizer"]
    limit = max_new_tokens or _max_new_tokens()

    if hasattr(tokenizer, "apply_chat_template"):
        messages = [{"role": "user", "content": prompt}]
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except (TypeError, ValueError, KeyError):
            text = prompt
    else:
        text = prompt

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=limit,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.pad_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


class _HFHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug(fmt, *args)

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/health":
            self.send_error(404)
            return
        body = json.dumps({"status": "ok", "model": hf_model_id()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/generate":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return
        prompt = str(payload.get("prompt") or payload.get("query") or "")
        max_new = payload.get("max_new_tokens")
        text = generate_text(
            prompt,
            max_new_tokens=int(max_new) if max_new is not None else None,
        )
        body = json.dumps({"text": text, "model": hf_model_id()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(*, block: bool = False) -> ThreadingHTTPServer:
    host = os.environ.get("ACE_HF_SERVER_HOST", _DEFAULT_HOST)
    port = int(os.environ.get("ACE_HF_SERVER_PORT", str(_DEFAULT_PORT)))
    load_model_bundle()
    server = ThreadingHTTPServer((host, port), _HFHandler)
    logger.info("HF inference server listening on %s:%s", host, port)
    if block:
        server.serve_forever()
    else:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    return server


def ensure_hf_server() -> str:
    """Start loopback HF server once; return base URL."""
    global _server_started  # noqa: PLW0603
    url = hf_server_url()
    with _server_lock:
        if _server_started:
            return url
        start_server(block=False)
        _server_started = True
    return url
