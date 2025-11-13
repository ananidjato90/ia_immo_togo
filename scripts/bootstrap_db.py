"""Create database tables for ImmoTogo."""
from __future__ import annotations

from immotogo.pipeline.models import Base
from immotogo.utils.db import get_engine


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database schema created")


if __name__ == "__main__":
    main()
