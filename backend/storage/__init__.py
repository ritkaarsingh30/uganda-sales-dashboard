import os
from .base import StorageBackend


def get_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "local":
        from .local import LocalStorage
        return LocalStorage()
    raise ValueError(f"Unsupported STORAGE_BACKEND: {backend!r}")
