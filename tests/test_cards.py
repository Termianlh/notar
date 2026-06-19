"""M1-b 测试：sign_card / verify_card。"""
import pytest

from notar.identity import create_identity, sign_card, verify_card


def _base_card(issuer_did: str) -> dict:
    return {"issuer": issuer_did, "name": "test-agent", "version": "1.0"}


# ── (a) 正例：sign → verify == True ────────────────────────────────────────────

def test_sign_then_verify():
    ident = create_identity()
    card = _base_card(ident.did)
    signed = sign_card(card, ident.private_key)
    assert verify_card(signed) is True


# ── (b) 反例：篡改任意字段后 verify == False ───────────────────────────────────

def test_verify_tampered_field():
    ident = create_identity()
    signed = sign_card(_base_card(ident.did), ident.private_key)
    tampered = {**signed, "name": "evil-agent"}
    assert verify_card(tampered) is False


# ── (c) 反例：冒充者——issuer=受害者 DID，但用攻击者私钥签 ──────────────────────

def test_verify_imposter_signer():
    victim = create_identity()
    attacker = create_identity()
    # 攻击者构造一张 issuer=受害者 DID 的 card，用自己的私钥签
    card = {"issuer": victim.did, "name": "imposter-agent"}
    signed_by_attacker = sign_card(card, attacker.private_key)
    # 验签时会从 issuer（受害者 DID）取公钥，与攻击者签名不匹配 → False
    assert verify_card(signed_by_attacker) is False


# ── (d) 反例：signature 缺失或畸形 → False，不抛异常 ──────────────────────────

@pytest.mark.parametrize("bad_card", [
    {"issuer": "did:key:z" + "A" * 44, "name": "x"},          # 缺 signature
    {"issuer": "did:key:z" + "A" * 44, "name": "x", "signature": "zz"},  # 非法 hex
])
def test_verify_missing_or_bad_signature(bad_card):
    assert verify_card(bad_card) is False


# ── (e) 正例：含中文 name 的 card sign→verify == True ─────────────────────────

def test_sign_verify_unicode_name():
    ident = create_identity()
    card = {"issuer": ident.did, "name": "测试智能体", "desc": "你好，世界"}
    signed = sign_card(card, ident.private_key)
    assert verify_card(signed) is True
