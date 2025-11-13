"""Database helpers using SQLAlchemy."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from immotogo.config import get_settings


Base = declarative_base()

_engine = None
_SessionFactory: sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.postgres_dsn, echo=False, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)
    return _SessionFactory


@contextmanager
def session_scope() -> Session:
    """Provide a transactional scope around a series of operations."""

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover
        session.rollback()
        raise
    finally:
        session.close()
