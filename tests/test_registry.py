"""M1-c 测试：Registry 三端点。"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from notar.identity import create_identity, sign_card
from registry.app import app
from registry.db import get_db
from registry.models import Agent, Base


@pytest.fixture
def client():
    # StaticPool：所有 session 复用同一连接，in-memory DB 数据才能跨请求持久
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_signed_card(name: str = "test-agent") -> tuple[dict, object]:
    ident = create_identity()
    card = {"issuer": ident.did, "name": name}
    return sign_card(card, ident.private_key), ident


# ── (a) 注册合法 card → 201，GET 拿回同一张 ──────────────────────────────────

def test_register_and_get(client):
    signed, _ = _make_signed_card()
    r = client.post("/register", json=signed)
    assert r.status_code == 201

    did = signed["issuer"]
    r2 = client.get(f"/agents/{did}")
    assert r2.status_code == 200
    assert r2.json()["issuer"] == did
    assert r2.json()["signature"] == signed["signature"]


# ── (b) 篡改 card → 422，DB 查不到 ────────────────────────────────────────────

def test_register_tampered_rejected(client):
    signed, _ = _make_signed_card()
    tampered = {**signed, "name": "evil-agent"}
    r = client.post("/register", json=tampered)
    assert r.status_code == 422

    r2 = client.get(f"/agents/{tampered['issuer']}")
    assert r2.status_code == 404


# ── (c) GET 不存在的 did → 404 ────────────────────────────────────────────────

def test_get_unknown_did(client):
    r = client.get("/agents/did:key:zThisDoesNotExist")
    assert r.status_code == 404


# ── (d) POST /verify 合法已注册 card → {valid:true, status:"active"} ──────────

def test_verify_valid_registered(client):
    signed, _ = _make_signed_card()
    client.post("/register", json=signed)

    r = client.post("/verify", json=signed)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["status"] == "active"
    assert body["did"] == signed["issuer"]


# ── (e) POST /verify 篡改 card → {valid:false} ────────────────────────────────

def test_verify_tampered(client):
    signed, _ = _make_signed_card()
    tampered = {**signed, "name": "evil-agent"}
    r = client.post("/verify", json=tampered)
    assert r.status_code == 200
    assert r.json()["valid"] is False


# ── (f) 同 DID 换内容重签再注册 → 更新成功，GET 拿到新 card ──────────────────

def test_reregister_updates_card(client):
    ident = create_identity()
    card_v1 = sign_card({"issuer": ident.did, "name": "v1"}, ident.private_key)
    card_v2 = sign_card({"issuer": ident.did, "name": "v2"}, ident.private_key)

    r1 = client.post("/register", json=card_v1)
    assert r1.status_code == 201

    r2 = client.post("/register", json=card_v2)
    assert r2.status_code == 201

    got = client.get(f"/agents/{ident.did}").json()
    assert got["name"] == "v2"
