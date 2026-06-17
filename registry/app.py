"""
注册中心 FastAPI 应用
路由:
  POST /register         — 注册新 agent（验签通过才入库）
  GET  /agents/{did}     — 按 DID 查询 agent card
  POST /verify           — 在线验证 DID 当前状态
"""
from __future__ import annotations
from fastapi import FastAPI

app = FastAPI(title="Notar Registry", version="0.1.0")


@app.post("/register")
async def register(body: dict) -> dict:
    # TODO: M3 实现（验签 → 入库）
    raise NotImplementedError


@app.get("/agents/{did}")
async def get_agent(did: str) -> dict:
    # TODO: M3 实现
    raise NotImplementedError


@app.post("/verify")
async def verify(body: dict) -> dict:
    # TODO: M3 实现
    raise NotImplementedError
