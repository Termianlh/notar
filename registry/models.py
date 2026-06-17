"""SQLAlchemy ORM 模型"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    did: Mapped[str] = mapped_column(String(256), primary_key=True)
    card_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False)
