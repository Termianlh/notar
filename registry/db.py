"""数据库 engine 与 session 工厂"""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notar.db")

# Render/Railway emit postgres:// but SQLAlchemy 2.x requires postgresql://
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI 依赖：提供数据库 session，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
