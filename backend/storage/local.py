import os
from pathlib import Path
from .base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self):
        data_path = os.getenv("UGANDA_DATA_PATH", "../UGANDA")
        backend_dir = Path(__file__).parent.parent
        self.root = (backend_dir / data_path).resolve()

    def get_file_bytes(self, relative_path: str) -> bytes:
        full_path = self.root / relative_path
        with open(full_path, "rb") as f:
            return f.read()

    def list_files(self, folder: str) -> list[str]:
        folder_path = self.root / folder
        if not folder_path.exists():
            return []
        return os.listdir(folder_path)

    def exists(self, relative_path: str) -> bool:
        return os.path.exists(self.root / relative_path)
