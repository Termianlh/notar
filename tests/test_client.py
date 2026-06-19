"""M2 测试：NotarClient 三方法（register / get_agent / verify）。"""
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from notar.identity import create_identity, sign_card
from notar.client import NotarClient
from registry.app import app
from registry.db import get_db
from registry.models import Base


@pytest.fixture
def nc():
    mem_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(mem_engine)
    TestSession = sessionmaker(bind=mem_engine)

    def override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    transport = httpx.ASGITransport(app=app)
    yield NotarClient("http://test", transport=transport)
    app.dependency_overrides.clear()


def _make_signed_card(name: str = "agent"):
    ident = create_identity()
    return sign_card({"issuer": ident.did, "name": name}, ident.private_key), ident


# ── (a) register 合法 card，再 get_agent 拿回同一张 ────────────────────────────

def test_register_and_get_agent(nc):
    signed, _ = _make_signed_card()
    result = nc.register(signed)
    assert result["registered"] is True
    assert result["did"] == signed["issuer"]

    card = nc.get_agent(signed["issuer"])
    assert card is not None
    assert card["issuer"] == signed["issuer"]
    assert card["signature"] == signed["signature"]


# ── (b) register 伪造 card → 422 → HTTPStatusError ────────────────────────────

def test_register_forged_raises(nc):
    signed, _ = _make_signed_card()
    forged = {**signed, "name": "evil"}
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        nc.register(forged)
    assert exc_info.value.response.status_code == 422


# ── (c) get_agent 不存在的 DID → None ────────────────────────────────────────

def test_get_agent_unknown_returns_none(nc):
    result = nc.get_agent("did:key:zThisDoesNotExist")
    assert result is None


# ── (d) verify 合法已注册 card → valid=True, status="active" ─────────────────

def test_verify_valid_registered(nc):
    signed, _ = _make_signed_card()
    nc.register(signed)

    result = nc.verify(signed)
    assert result["valid"] is True
    assert result["status"] == "active"
    assert result["did"] == signed["issuer"]


# ── (e) verify 篡改 card → valid=False ───────────────────────────────────────

def test_verify_tampered_returns_invalid(nc):
    signed, _ = _make_signed_card()
    tampered = {**signed, "name": "evil"}

    result = nc.verify(tampered)
    assert result["valid"] is False
