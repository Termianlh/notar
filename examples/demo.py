"""
Notar 端到端演示 — python examples/demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from notar.identity import create_identity, sign_card
from notar.client import NotarClient
from registry.app import app
from registry.db import get_db
from registry.models import Base

SEP = "──" * 28

def step(n, title):  print(f"\n{n} {title}")
def ok(msg):         print(f"   ✅ {msg}")
def fail(msg):       print(f"   ❌ {msg}")
def info(msg):       print(f"   {msg}")


def _setup_registry() -> NotarClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    return NotarClient("http://demo", transport=httpx.ASGITransport(app=app))


def main():
    nc = _setup_registry()

    print("Notar 端到端演示")
    print(SEP)

    # ① Alice 创建身份
    step("①", "Alice 创建身份")
    alice = create_identity()
    info(f"DID: {alice.did}")

    # ② Alice 签名并注册
    step("②", "Alice 签名并注册到 registry")
    alice_card = sign_card({"issuer": alice.did, "name": "Alice", "role": "agent"}, alice.private_key)
    nc.register(alice_card)
    ok("登记成功")

    # ③ Bob 查询 + 验证
    step("③", "Bob 查询 + 验证 Alice 的身份")
    card = nc.get_agent(alice.did)
    info(f"卡片：name={card['name']!r}, role={card['role']!r}")
    result = nc.verify(alice_card)
    assert result["valid"] and result["status"] == "active"
    ok("Alice 身份可信（status: active）")

    # ④ Eve 冒充 Alice
    step("④", "Eve 冒充 Alice（issuer=Alice.DID，用 Eve 的私钥签名）")
    eve = create_identity()
    fake_card = sign_card({"issuer": alice.did, "name": "Eve-as-Alice"}, eve.private_key)
    try:
        nc.register(fake_card)
        print("   [BUG] 应被拒绝！")
        sys.exit(1)
    except Exception as e:
        fail(f"冒充者无法注册成 Alice（422 验签失败）")

    # ⑤ 篡改 Alice 的卡片
    step("⑤", "攻击者篡改 Alice 的合法卡片（name 改为 'evil-alice'）")
    tampered = {**alice_card, "name": "evil-alice"}
    result = nc.verify(tampered)
    assert result["valid"] is False
    fail("篡改卡片验证无效（valid=False）")

    # ⑥ Eve 用自己的身份正常注册
    step("⑥", "Eve 用自己的 DID 正常注册")
    eve_card = sign_card({"issuer": eve.did, "name": "Eve", "role": "agent"}, eve.private_key)
    nc.register(eve_card)
    ok("Eve 自己的身份注册成功（做自己可以，冒充别人不行）")

    print(f"\n{SEP}")
    print("演示完成，所有断言通过。")


if __name__ == "__main__":
    main()
