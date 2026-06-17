"""
身份模块：keygen / did:key 编码 / agent card / 签名 / 验证
"""
from __future__ import annotations
from typing import Any


def create_identity() -> dict[str, Any]:
    """
    生成 Ed25519 密钥对，返回:
    {
        "did": "did:key:z...",
        "private_key_bytes": bytes,  # 调用方负责安全存储，绝不持久化
    }
    """
    # TODO: M1 实现
    raise NotImplementedError


def _did_from_public_key(public_key_bytes: bytes) -> str:
    """Ed25519 公钥 → did:key (multicodec 0xed01 + base58btc)"""
    # TODO: M1 实现
    raise NotImplementedError


def sign_card(card: dict[str, Any], private_key_bytes: bytes) -> dict[str, Any]:
    """
    对 card 签名，返回带 signature 字段的新 card。
    规范化：json.dumps(card_without_sig, sort_keys=True, separators=(",",":"))
    """
    # TODO: M1 实现
    raise NotImplementedError


def verify_card(card: dict[str, Any]) -> bool:
    """
    验证 card.signature，DID 公钥须与签名匹配。
    规范化方式与 sign_card 完全一致。
    """
    # TODO: M1 实现
    raise NotImplementedError
