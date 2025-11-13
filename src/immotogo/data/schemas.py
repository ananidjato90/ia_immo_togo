"""Pydantic data models used across the pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Iterable

from pydantic import BaseModel, HttpUrl, PositiveFloat, field_validator


class PropertyType(str, Enum):
    """Enumeration describing supported property categories."""

    apartment = "appartement"
    house = "maison"
    office = "bureau"
    land = "terrain"
    commercial = "commercial"
    room = "chambre"
    other = "autre"


class TransactionType(str, Enum):
    """Enumeration describing supported transaction types."""

    rent = "location"
    sale = "vente"
    buy = "achat"
    lease = "bail"


class Listing(BaseModel):
    """Canonical representation of a real-estate listing."""

    id: str
    source: str
    title: str
    description: str
    property_type: PropertyType
    transaction_type: TransactionType
    city: str | None = None
    district: str | None = None
    country: str = "Togo"
    price: PositiveFloat | None = None
    currency: str = "XOF"
    surface_m2: PositiveFloat | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    amenities: list[str] = []
    contact: str | None = None
    url: HttpUrl
    images: list[HttpUrl] = []
    scraped_at: datetime
    published_at: datetime | None = None

    @field_validator("amenities", mode="before")
    @classmethod
    def _normalize_amenities(cls, value: Iterable[str] | None) -> list[str]:
        if value is None:
            return []
        return sorted({item.strip() for item in value if item and item.strip()})


class ListingChunk(BaseModel):
    """Chunked representation used for embedding and retrieval."""

    listing_id: str
    source: str
    text: str
    chunk_index: int


class ListingQuery(BaseModel):
    """User query structure passed to the retrieval pipeline."""

    query: str
    max_results: int = 8
    require_structured: bool = True


class GeneratedAnswer(BaseModel):
    """Model response that combines natural language and structured data."""

    query: ListingQuery
    answer: str
    listings: list[Listing]
    used_chunks: list[ListingChunk]
    model_name: str
    generated_at: datetime
