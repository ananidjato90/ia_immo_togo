"""Ingestion pipeline to persist listings and populate vector store."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Sequence

from sqlalchemy import delete

from immotogo.data.schemas import Listing, ListingChunk
from immotogo.pipeline.models import ListingChunkORM, ListingORM
from immotogo.pipeline.embeddings import add_documents
from immotogo.utils.db import session_scope


def chunk_listing(listing: Listing, chunk_size: int = 400) -> list[ListingChunk]:
    """Create retrieval-friendly text chunks from a listing."""

    base_text_parts = [
        listing.title,
        listing.description,
        f"Type: {listing.property_type.value}",
        f"Transaction: {listing.transaction_type.value}",
        f"Ville: {listing.city or 'Non précisé'}",
        f"Quartier: {listing.district or 'Non précisé'}",
    ]
    if listing.price:
        base_text_parts.append(f"Prix: {listing.price} {listing.currency}")
    if listing.surface_m2:
        base_text_parts.append(f"Surface: {listing.surface_m2} m²")
    if listing.bedrooms:
        base_text_parts.append(f"Chambres: {listing.bedrooms}")
    if listing.amenities:
        base_text_parts.append("Equipements: " + ", ".join(listing.amenities))

    combined_text = " \n".join(base_text_parts)
    tokens = combined_text.split()

    chunks: list[ListingChunk] = []
    for index in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[index : index + chunk_size]
        if not chunk_tokens:
            continue
        chunk_text = " ".join(chunk_tokens)
        chunks.append(
            ListingChunk(
                listing_id=listing.id,
                source=listing.source,
                text=chunk_text,
                chunk_index=index // chunk_size,
            )
        )
    if not chunks:
        chunks.append(
            ListingChunk(
                listing_id=listing.id,
                source=listing.source,
                text=combined_text,
                chunk_index=0,
            )
        )
    return chunks


def upsert_listings(listings: Sequence[Listing]) -> list[ListingChunk]:
    """Persist listings and return the generated chunks."""

    chunks: list[ListingChunk] = []
    with session_scope() as session:
        for listing in listings:
            existing = session.get(ListingORM, listing.id)
            if existing:
                _update_listing(existing, listing)
                session.flush()
                session.execute(
                    delete(ListingChunkORM).where(ListingChunkORM.listing_id == listing.id)
                )
            else:
                existing = ListingORM(id=listing.id)
                session.add(existing)
                _update_listing(existing, listing)
            listing_chunks = chunk_listing(listing)
            for chunk in listing_chunks:
                session.add(
                    ListingChunkORM(
                        listing_id=chunk.listing_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                    )
                )
            chunks.extend(listing_chunks)
    return chunks


def index_chunks(chunks: Iterable[ListingChunk]) -> list[str]:
    texts: list[str] = []
    metadatas: list[dict[str, str]] = []
    for chunk in chunks:
        texts.append(chunk.text)
        metadatas.append({
            "listing_id": chunk.listing_id,
            "source": chunk.source,
            "chunk_index": str(chunk.chunk_index),
        })
    if not texts:
        return []
    return add_documents(texts, metadatas)


def ingest(listings: Sequence[Listing]) -> list[str]:
    chunks = upsert_listings(listings)
    return index_chunks(chunks)


def _update_listing(target: ListingORM, source: Listing) -> None:
    target.source = source.source
    target.title = source.title
    target.description = source.description
    target.property_type = source.property_type.value
    target.transaction_type = source.transaction_type.value
    target.city = source.city
    target.district = source.district
    target.country = source.country
    target.price = source.price
    target.currency = source.currency
    target.surface_m2 = source.surface_m2
    target.bedrooms = source.bedrooms
    target.bathrooms = source.bathrooms
    target.amenities = source.amenities
    target.contact = source.contact
    target.url = str(source.url)
    target.images = [str(image) for image in source.images]
    target.scraped_at = source.scraped_at
    target.published_at = source.published_at
    target.raw_payload = source.model_dump(mode="json")
