import os
from .base import StorageBackend


def get_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        from .local import LocalStorage
        return LocalStorage()
    if backend == "sheets":
        from .sheets import SheetStorage
        return SheetStorage()
    raise ValueError(f"Unsupported STORAGE_BACKEND: {backend!r}")
