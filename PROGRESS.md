# Notar 项目进度

## 已完成：M2 — SDK Client（NotarClient）

**pytest 结果**：25 passed in 0.60s（全绿，M1 20 + M2 5）

### 新增 / 修改的文件
- `sdk/notar/client.py` — 完整实现 `NotarClient`：
  - `register(card)` → POST /register；422 验签失败明确抛 `httpx.HTTPStatusError`
  - `get_agent(did)` → GET /agents/{did}；404 返回 `None`，其他非 2xx 抛
  - `verify(card) -> dict` → POST /verify；返回 `{"valid", "did", "status"}`
  - 内部用 `httpx.AsyncClient` + `anyio.run()` 桥接，对外暴露同步接口
  - `transport` 参数注入 `httpx.ASGITransport` 供测试用（不走网络）
- `sdk/notar/__init__.py` — 增加 `NotarClient` 导出
- `tests/test_client.py` — 5 个测试：(a) 注册+查询往返 (b) 伪造422 (c) 不存在DID→None (d) verify合法→active (e) verify篡改→invalid

### 关键设计
- `anyio.run()` 在新事件循环里运行 async 代码，sync 测试无需 `@pytest.mark.anyio`
- 每次调用独立创建 `AsyncClient`（context manager），不共享连接状态
- 安全约束：三方法只传 card dict（公开数据），绝不序列化 `private_key`

---

## 已完成：M1-c — Registry 三端点

**pytest 结果**：20 passed in 0.53s（全绿，M1-a 8 + M1-b 6 + M1-c 6）

### 新增 / 修改的文件
- `registry/__init__.py` — 空文件，使 registry 成为可导入 Python 包
- `registry/app.py` — 完整实现三端点：
  - `POST /register`：`CardIn` Pydantic 校验 → `verify_card` → 422 或入库（201）；重注册只更新 `card_json`
  - `GET /agents/{did:path}`：按 DID 查询，含冒号的 DID 由 `{did:path}` 捕获；404 on miss
  - `POST /verify`：独立验签 + 查 DB 状态（`active` / `unknown`）
  - lifespan 建表（现代写法，无 DeprecationWarning）
- `conftest.py`（项目根）— `sys.path.insert(0, ...)` 让 pytest 能导入 `registry` 包
- `tests/test_registry.py` — 6 个测试，用 `StaticPool` in-memory SQLite + `dependency_overrides` 完全隔离

### 关键设计约束
- `verify_card` 失败 → 422，绝不入库，保持"里面的都验过"的不变量
- 重注册权限来自签名本身（只有持私钥者才能过验签），无需额外鉴权
- `status` 从 `Agent.revoked` 字段派生（False=active，None=unknown），无冗余列
- SQLite in-memory 测试需 `StaticPool`，否则每次新连接得到空库

---

## 已完成：M1-a — Identity 生成与 did:key 编解码

**pytest 结果**：8 passed in 0.46s（全绿）

### 新增 / 修改的文件
- `sdk/notar/identity.py` — 实现了：
  - `Identity` dataclass（`did`, `public_key`, `private_key`；`private_key` 设 `repr=False`）
  - `_did_from_public_key(pub_bytes)` — 内部函数，拼 multicodec 0xED01 + base58btc + "did:key:z"
  - `create_identity()` — Ed25519 keygen，返回 `Identity`
  - `public_key_from_did(did)` — 逆向解码 DID，含 5 层校验，错误抛 `ValueError`
  - `sign_card` / `verify_card` 维持 `NotImplementedError` 占位（M1-b）
- `sdk/notar/__init__.py` — 导出 `Identity`, `create_identity`, `public_key_from_did`
- `tests/test_identity.py` — 8 个测试（含 4 个反例参数化），覆盖格式/往返/确定性/畸形DID
- `tests/test_placeholder.py` — 已删除（被 test_identity.py 覆盖）

### did:key 编码规范（Ed25519）
```
raw_pub (32 bytes)
  → 前拼 bytes([0xED, 0x01])   # multicodec ed25519-pub varint
  → base58btc 编码
  → "z" + encoded              # multibase prefix
  → "did:key:z" + encoded
```

---

## 已完成：M0 — 脚手架搭建

**提交**：`d77462a` — chore: scaffold notar project (no logic, stubs only)

### 已创建的文件
- `sdk/notar/__init__.py`, `identity.py`, `client.py`
- `registry/app.py`, `db.py`, `models.py`
- `examples/demo.py`
- `pyproject.toml` / `.gitignore` / `.env.example` / `README.md`

---

## 已完成：M1-b — sign_card + verify_card

**pytest 结果**：14 passed in 0.56s（全绿，M1-a 8 + M1-b 6）

### 新增 / 修改的文件
- `sdk/notar/identity.py` — 新增：
  - `_canonical(card)` 内部函数：排除 `"signature"` 后 `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()`
  - `sign_card(card, private_key: Ed25519PrivateKey)` — 返回含 hex signature 的新 card，不修改原 card
  - `verify_card(card)` — 捕获 `InvalidSignature / KeyError / ValueError` 返回 False，意料外异常传播
- `tests/test_cards.py` — 6 个测试（含 2 个参数化）：
  - (a) sign → verify == True
  - (b) 篡改字段 → False
  - (c) 冒充者（issuer=受害者 DID，攻击者私钥签）→ False
  - (d) 缺 signature / 畸形 hex → False，不抛
  - (e) 含中文 name → sign→verify == True

### 设计约束（registry / demo 据此对接）
- card 签名者字段名锁死为 `"issuer"`
- signature 存 hex 字符串
- 规范化：所有组件只调 `_canonical()`，不重复

---

## 下一步：M1-c — Registry 对接（建议）

建议方向：
1. FastAPI `POST /register` 调 `verify_card` 校验 card 后存 DB
2. `GET /agents/{did}` 返回已注册 agent card
3. `POST /verify` 接收 card，返回验签结果 JSON
4. `examples/demo.py` 演示端到端：生成 → 签名 → 注册 → 查询 → 篡改被拒
