from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.sql import func
from .db import Base

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    api_key: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_uri: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="null")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Usage(Base):
    __tablename__ = "usage_monthly"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    docs_parsed: Mapped[int] = mapped_column(Integer, default=0)

class Webhook(Base):
    __tablename__ = "webhooks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    url: Mapped[str] = mapped_column(String(1024))
