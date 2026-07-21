import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Float, Text, Enum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


def gen_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class ImageStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    original_filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    status = Column(Enum(ImageStatus), nullable=False, default=ImageStatus.pending)
    failure_reason = Column(Text, nullable=True)

    uploaded_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    results = relationship("AnalysisResult", back_populates="image", cascade="all, delete-orphan")
    phash_entry = relationship("ImageHash", back_populates="image", uselist=False, cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    image_id = Column(UUID(as_uuid=False), ForeignKey("images.id"), nullable=False, index=True)

    check_name = Column(String, nullable=False)
    passed = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0, how sure the check is
    detail = Column(Text, nullable=True)  # human-readable explanation / extracted data

    created_at = Column(DateTime(timezone=True), default=utcnow)

    image = relationship("Image", back_populates="results")


class ImageHash(Base):
    """Perceptual hash stored separately so duplicate lookups don't scan the whole images table."""
    __tablename__ = "image_hashes"

    image_id = Column(UUID(as_uuid=False), ForeignKey("images.id"), primary_key=True)
    phash = Column(String, nullable=False, index=True)

    image = relationship("Image", back_populates="phash_entry")
