"""Field-level and selective encryption for sensitive inputs."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

from cryptography.fernet import Fernet


@dataclass
class EncryptedField:
    """Wrapper for selectively encrypted input fields."""

    name: str
    ciphertext: bytes
    label: str = "SECRET"

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "label": self.label,
        }


@dataclass
class FieldEncryptionRegistry:
    """Selective field-level encryption using Fernet (AES-128-CBC + HMAC).

    ADR: Field encryption limits blast radius of in-memory exposure; it does
    not prevent all side channels from neural compression.
    """

    _key: bytes = field(default_factory=Fernet.generate_key)
    _encrypted_fields: dict[str, EncryptedField] = field(default_factory=dict)

    @property
    def fernet(self) -> Fernet:
        return Fernet(self._key)

    def encrypt_field(
        self, name: str, value: Any, label: str = "SECRET"
    ) -> EncryptedField:
        plaintext = json.dumps(value).encode()
        ciphertext = self.fernet.encrypt(plaintext)
        enc = EncryptedField(name=name, ciphertext=ciphertext, label=label)
        self._encrypted_fields[name] = enc
        return enc

    def decrypt_field(self, enc: EncryptedField) -> Any:
        plaintext = self.fernet.decrypt(enc.ciphertext)
        return json.loads(plaintext.decode())

    def encrypt_payload_fields(
        self,
        payload: dict[str, Any],
        sensitive_keys: set[str],
    ) -> dict[str, Any]:
        """Encrypt only designated sensitive keys; leave others plaintext."""
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if key in sensitive_keys:
                enc = self.encrypt_field(key, value)
                result[key] = enc.to_dict()
            else:
                result[key] = value
        return result

    def decrypt_payload_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, dict) and "ciphertext" in value:
                enc = EncryptedField(
                    name=value["name"],
                    ciphertext=base64.b64decode(value["ciphertext"]),
                    label=value.get("label", "SECRET"),
                )
                result[key] = self.decrypt_field(enc)
            else:
                result[key] = value
        return result

    def list_encrypted(self) -> list[str]:
        return list(self._encrypted_fields.keys())
