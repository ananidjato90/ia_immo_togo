"""Retrieval-Augmented Generation pipeline using Mistral."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from huggingface_hub import InferenceClient
from langchain.schema import Document

from immotogo.config import get_settings
from immotogo.data.schemas import (
    GeneratedAnswer,
    Listing,
    ListingChunk,
    ListingQuery,
    PropertyType,
    TransactionType,
)
from immotogo.pipeline.embeddings import get_vector_store
from immotogo.pipeline.models import ListingORM
from immotogo.utils.db import session_scope


class MistralGenerator:
    """Thin wrapper around Hugging Face text-generation inference."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = InferenceClient(model=settings.hf_mistral_model, token=settings.hf_token)
        self.settings = settings

    def generate(self, prompt: str) -> str:
        response = self.client.text_generation(
            prompt,
            max_new_tokens=self.settings.mistral_max_output_tokens,
            temperature=self.settings.mistral_temperature,
            top_p=self.settings.mistral_top_p,
            do_sample=True,
        )
        return response


class RetrievalAugmentedGenerator:
    """Main RAG orchestrator."""

    def __init__(self) -> None:
        self.vector_store = get_vector_store()
        self.generator = MistralGenerator()

    def answer(self, query: ListingQuery) -> GeneratedAnswer:
        docs = self.vector_store.similarity_search_with_score(query.query, k=query.max_results)
        listings = self._hydrate_listings(doc for doc, _ in docs)
        chunks = self._build_chunks(doc for doc, _ in docs)
        prompt = self._build_prompt(query.query, listings, chunks)
        completion = self.generator.generate(prompt)
        return GeneratedAnswer(
            query=query,
            answer=completion,
            listings=listings,
            used_chunks=chunks,
            model_name=self.generator.settings.hf_mistral_model,
            generated_at=datetime.utcnow(),
        )

    def _hydrate_listings(self, documents: Iterable[Document]) -> list[Listing]:
        listing_ids = {doc.metadata.get("listing_id") for doc in documents}
        if not listing_ids:
            return []
        with session_scope() as session:
            rows: list[ListingORM] = (
                session.query(ListingORM)
                .filter(ListingORM.id.in_(listing_ids))
                .all()
            )
        return [self._to_listing(row) for row in rows]

    def _build_chunks(self, documents: Iterable[Document]) -> list[ListingChunk]:
        chunks: list[ListingChunk] = []
        for doc in documents:
            metadata = doc.metadata or {}
            chunks.append(
                ListingChunk(
                    listing_id=metadata.get("listing_id", ""),
                    source=metadata.get("source", ""),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    text=doc.page_content,
                )
            )
        return chunks

    def _build_prompt(
        self,
        question: str,
        listings: list[Listing],
        chunks: list[ListingChunk],
    ) -> str:
        context_lines = ["Tu es un expert en immobilier du Togo."]
        for listing in listings:
            context_lines.append(
                "\n".join(
                    [
                        f"Annonce: {listing.title}",
                        f"Type: {listing.property_type.value}",
                        f"Transaction: {listing.transaction_type.value}",
                        f"Localisation: {listing.city or 'Non précisé'}",
                        f"Prix: {listing.price or 'N/A'} {listing.currency}",
                        f"Surface: {listing.surface_m2 or 'N/A'} m²",
                        f"Description: {listing.description[:400]}...",
                        f"Lien: {listing.url}",
                    ]
                )
            )
        prompt = (
            "SYSTEM:\n"
            + "\n".join(context_lines)
            + "\n\nUSER:\n"
            + question
            + "\n\nTu dois répondre en français clair, proposer un résumé puis une liste structurée des annonces pertinentes."
        )
        return prompt

    def _to_listing(self, row: ListingORM) -> Listing:
        return Listing(
            id=row.id,
            source=row.source,
            title=row.title,
            description=row.description,
            property_type=PropertyType(row.property_type),
            transaction_type=TransactionType(row.transaction_type),
            city=row.city,
            district=row.district,
            country=row.country,
            price=row.price,
            currency=row.currency,
            surface_m2=row.surface_m2,
            bedrooms=row.bedrooms,
            bathrooms=row.bathrooms,
            amenities=row.amenities or [],
            contact=row.contact,
            url=row.url,
            images=row.images or [],
            scraped_at=row.scraped_at,
            published_at=row.published_at,
        )
