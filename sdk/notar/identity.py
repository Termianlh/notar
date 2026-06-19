"""
身份模块：keygen / did:key 编码 / agent card / 签名 / 验证
"""
from __future__ import annotations

import base58
import json
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

_MULTICODEC_ED25519_PUB = bytes([0xED, 0x01])


@dataclass
class Identity:
    did: str
    public_key: Ed25519PublicKey
    private_key: Ed25519PrivateKey = field(repr=False)  # never appears in repr/logs


def _did_from_public_key(public_key_bytes: bytes) -> str:
    """Ed25519 raw public key bytes → did:key string."""
    encoded = base58.b58encode(_MULTICODEC_ED25519_PUB + public_key_bytes).decode()
    return "did:key:z" + encoded


def create_identity() -> Identity:
    """生成 Ed25519 密钥对，返回 Identity。私钥仅存于对象内，绝不序列化。"""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return Identity(
        did=_did_from_public_key(pub_bytes),
        public_key=pub,
        private_key=priv,
    )


def public_key_from_did(did: str) -> Ed25519PublicKey:
    """did:key → Ed25519PublicKey。所有格式错误抛 ValueError。"""
    if not did.startswith("did:key:z"):
        raise ValueError(f"missing 'did:key:z' prefix: {did!r}")

    encoded = did[len("did:key:z"):]
    try:
        raw = base58.b58decode(encoded)
    except Exception as exc:
        raise ValueError(f"invalid base58btc encoding in DID: {did!r}") from exc

    if len(raw) < 2 or raw[0] != 0xED or raw[1] != 0x01:
        raise ValueError(
            f"invalid multicodec prefix (expected 0xED 0x01, got "
            f"{raw[:2].hex() if len(raw) >= 2 else raw.hex()!r}): {did!r}"
        )

    pub_bytes = raw[2:]
    if len(pub_bytes) != 32:
        raise ValueError(
            f"wrong key length: {len(pub_bytes)} bytes (expected 32): {did!r}"
        )

    try:
        return Ed25519PublicKey.from_public_bytes(pub_bytes)
    except Exception as exc:
        raise ValueError(f"invalid Ed25519 public key bytes in DID: {did!r}") from exc


def _canonical(card: dict[str, Any]) -> bytes:
    """排除 signature 字段后的规范化字节，sign 和 verify 共用，不重复。"""
    payload = {k: v for k, v in card.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign_card(card: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    """对 card 签名，返回带 signature 字段的新 card（不修改原 card）。"""
    sig = private_key.sign(_canonical(card))
    return {**card, "signature": sig.hex()}


def verify_card(card: dict[str, Any]) -> bool:
    """
    验证 card.signature。从 card["issuer"] 取公钥，重建规范化字节后验签。
    预期内失败（InvalidSignature / KeyError / ValueError）返回 False。
    意料外异常不吞，让其传播。
    """
    try:
        pub = public_key_from_did(card["issuer"])
        sig_bytes = bytes.fromhex(card["signature"])
        pub.verify(sig_bytes, _canonical(card))
        return True
    except (InvalidSignature, KeyError, ValueError):
        return False
