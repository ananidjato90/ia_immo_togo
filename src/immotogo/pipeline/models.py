"""SQLAlchemy ORM models for storage."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from immotogo.utils.db import Base


class ListingORM(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(length=512), primary_key=True)
    source: Mapped[str] = mapped_column(String(length=64), nullable=False)
    title: Mapped[str] = mapped_column(String(length=512), nullable=False)
    description: Mapped[str] = mapped_column(String(length=5000), nullable=False)
    property_type: Mapped[str] = mapped_column(String(length=32), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(length=32), nullable=False)
    city: Mapped[str | None] = mapped_column(String(length=128))
    district: Mapped[str | None] = mapped_column(String(length=128))
    country: Mapped[str] = mapped_column(String(length=64), default="Togo", nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(length=8), default="XOF", nullable=False)
    surface_m2: Mapped[float | None] = mapped_column(Float)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    amenities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contact: Mapped[str | None] = mapped_column(String(length=256))
    url: Mapped[str] = mapped_column(String(length=512), nullable=False)
    images: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    chunks: Mapped[list["ListingChunkORM"]] = relationship(
        "ListingChunkORM", back_populates="listing", cascade="all, delete-orphan"
    )


class ListingChunkORM(Base):
    __tablename__ = "listing_chunks"
    __table_args__ = (UniqueConstraint("listing_id", "chunk_index", name="uq_listing_chunk"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    listing: Mapped[ListingORM] = relationship("ListingORM", back_populates="chunks")
