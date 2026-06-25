from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def get_file_bytes(self, relative_path: str) -> bytes:
        pass

    @abstractmethod
    def list_files(self, folder: str) -> list[str]:
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    def list_dirs(self, folder: str = "") -> list[str]:
        pass
