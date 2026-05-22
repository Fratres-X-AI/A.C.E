"""Tests for field-level encryption."""

from aegis.crypto.encryption_fields import FieldEncryptionRegistry


def test_encrypt_decrypt_roundtrip() -> None:
    reg = FieldEncryptionRegistry()
    enc = reg.encrypt_field("secret_key", {"value": 42})
    decrypted = reg.decrypt_field(enc)
    assert decrypted == {"value": 42}


def test_selective_field_encryption() -> None:
    reg = FieldEncryptionRegistry()
    payload = {"public": "hello", "secret": "classified"}
    encrypted = reg.encrypt_payload_fields(payload, {"secret"})
    assert encrypted["public"] == "hello"
    assert isinstance(encrypted["secret"], dict)
    assert "ciphertext" in encrypted["secret"]
    restored = reg.decrypt_payload_fields(encrypted)
    assert restored == payload


def test_list_encrypted_fields() -> None:
    reg = FieldEncryptionRegistry()
    reg.encrypt_field("a", 1)
    reg.encrypt_field("b", 2)
    assert set(reg.list_encrypted()) == {"a", "b"}
