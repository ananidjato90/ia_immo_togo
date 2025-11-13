"""FastAPI application exposing the ImmoTogo search service."""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException

from immotogo.data.schemas import GeneratedAnswer, ListingQuery
from immotogo.pipeline.rag import RetrievalAugmentedGenerator

logger = logging.getLogger(__name__)
app = FastAPI(title="ImmoTogo AI", version="0.1.0")


def get_rag() -> RetrievalAugmentedGenerator:
    return RetrievalAugmentedGenerator()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=GeneratedAnswer)
async def search(query: ListingQuery, rag: RetrievalAugmentedGenerator = Depends(get_rag)) -> GeneratedAnswer:
    try:
        return rag.answer(query)
    except Exception as exc:  # pragma: no cover
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(exc))
