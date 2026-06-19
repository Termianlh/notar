"""
注册中心 FastAPI 应用
路由:
  POST /register         — 注册新 agent（验签通过才入库）
  GET  /agents/{did}     — 按 DID 查询 agent card
  POST /verify           — 在线验证 DID 当前状态
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from notar.identity import verify_card
from .db import engine, get_db
from .models import Agent, Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Notar Registry", version="0.1.0", lifespan=lifespan)


class CardIn(BaseModel):
    issuer: str
    signature: str
    model_config = ConfigDict(extra="allow")


@app.post("/register", status_code=201)
async def register(body: CardIn, db: Session = Depends(get_db)) -> dict:
    card = body.model_dump()
    if not verify_card(card):
        raise HTTPException(status_code=422, detail="invalid card signature")
    did = card["issuer"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    agent = db.get(Agent, did)
    if agent:
        agent.card_json = json.dumps(card)
    else:
        db.add(Agent(did=did, card_json=json.dumps(card), created_at=now))
    db.commit()
    return {"registered": True, "did": did}


@app.get("/agents/{did:path}")
async def get_agent(did: str, db: Session = Depends(get_db)) -> dict:
    agent = db.get(Agent, did)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    return json.loads(agent.card_json)


@app.post("/verify")
async def verify(body: CardIn, db: Session = Depends(get_db)) -> dict:
    card = body.model_dump()
    valid = verify_card(card)
    did = card["issuer"]
    agent = db.get(Agent, did)
    status = "active" if (agent and not agent.revoked) else "unknown"
    return {"valid": valid, "did": did, "status": status}
