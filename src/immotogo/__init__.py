"""ImmoTogo AI package."""

from importlib.metadata import version

__all__ = ["__version__"]


def __getattr__(name: str):
    if name == "__version__":
        try:
            return version("immotogo")
        except Exception as exc:  # pragma: no cover
            raise AttributeError("Package metadata not available") from exc
    raise AttributeError(name)
