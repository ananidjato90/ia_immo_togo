"""Embedding helpers for the ImmoTogo pipeline."""
from __future__ import annotations

from typing import Sequence

from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from immotogo.config import get_settings


def get_embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    return HuggingFaceEmbeddings(
        model_name=settings.hf_embedding_model,
        cache_folder=settings.cache_directory,
        model_kwargs={"device": "cpu"},
    )


def get_vector_store(collection_name: str = "immotogo_listings") -> Chroma:
    settings = get_settings()
    embeddings = get_embeddings()
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_persist_directory),
    )


def add_documents(texts: Sequence[str], metadatas: Sequence[dict[str, str]]) -> list[str]:
    store = get_vector_store()
    ids = store.add_texts(list(texts), list(metadatas))
    store.persist()
    return ids
