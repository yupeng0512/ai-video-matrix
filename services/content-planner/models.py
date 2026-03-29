"""SQLAlchemy models for content-planner service."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Float, Integer, BigInteger,
    DateTime, Enum as PgEnum, ForeignKey, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class HookType(str, enum.Enum):
    question = "question"
    suspense = "suspense"
    data = "data"
    empathy = "empathy"


class StyleType(str, enum.Enum):
    recommend = "recommend"
    review = "review"
    tutorial = "tutorial"
    story = "story"


class DurationType(str, enum.Enum):
    s15 = "15s"
    s30 = "30s"
    s60 = "60s"


class ScriptStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    assigned = "assigned"
    published = "published"
    failed = "failed"


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    keywords = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    scripts = relationship("ScriptVariant", back_populates="product")


class ScriptVariant(Base):
    __tablename__ = "script_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    hook = Column(PgEnum(HookType, name="hook_type", create_type=False), nullable=False)
    style = Column(PgEnum(StyleType, name="style_type", create_type=False), nullable=False)
    duration = Column(PgEnum(DurationType, name="duration_type", create_type=False), nullable=False)
    prompt_text = Column(Text, nullable=False)
    visual_desc = Column(Text)
    tts_text = Column(Text)
    fingerprint_hash = Column(String(64))
    status = Column(PgEnum(ScriptStatus, name="script_status", create_type=False), nullable=False, default=ScriptStatus.pending)
    assigned_account = Column(UUID(as_uuid=True))
    assigned_platform = Column(String(32))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="scripts")
