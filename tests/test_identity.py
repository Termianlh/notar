"""M1-a 测试：identity 生成与 did:key 编解码。"""
import base58
import pytest
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from notar.identity import (
    Identity,
    _did_from_public_key,
    create_identity,
    public_key_from_did,
)

_MULTICODEC_ED25519_PUB = bytes([0xED, 0x01])


# ── (a) DID 格式 ──────────────────────────────────────────────────────────────

def test_did_format():
    ident = create_identity()
    assert ident.did.startswith("did:key:z")
    encoded = ident.did[len("did:key:z"):]
    raw = base58.b58decode(encoded)
    assert raw[:2] == _MULTICODEC_ED25519_PUB
    assert len(raw[2:]) == 32


def test_identity_fields():
    ident = create_identity()
    assert isinstance(ident, Identity)
    assert isinstance(ident.did, str)
    # private_key must not appear in repr
    assert "private_key" not in repr(ident)


# ── (b) 公钥往返 ──────────────────────────────────────────────────────────────

def test_pubkey_roundtrip():
    ident = create_identity()
    recovered = public_key_from_did(ident.did)
    orig = ident.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    got = recovered.public_bytes(Encoding.Raw, PublicFormat.Raw)
    assert orig == got


# ── (c) 确定性 ────────────────────────────────────────────────────────────────

def test_did_deterministic():
    ident = create_identity()
    priv_bytes = ident.private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )
    # reconstruct from the same raw private key bytes
    priv2 = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    pub2_bytes = priv2.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    assert ident.did == _did_from_public_key(pub2_bytes)


# ── (d) 反例：畸形 DID 被明确拒绝 ────────────────────────────────────────────

_WRONG_MULTICODEC_DID = (
    "did:key:z"
    + base58.b58encode(bytes([0x00, 0x01]) + bytes(32)).decode()
)

@pytest.mark.parametrize("bad_did", [
    "did:key:abc",                  # 缺 'z' multibase 前缀
    "did:web:example.com",          # 错误 DID method
    "did:key:z" + "0OIl" * 10,     # 非法 base58 字符 (0, O, I, l 不在字母表)
    _WRONG_MULTICODEC_DID,          # 正确 base58 但 multicodec 前缀错
])
def test_invalid_did_rejected(bad_did):
    with pytest.raises(ValueError):
        public_key_from_did(bad_did)
