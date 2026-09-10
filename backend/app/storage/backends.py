import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    def save_stream(self, stream: BinaryIO, key: str, max_bytes: int | None = None) -> int:
        raise NotImplementedError

    @abstractmethod
    def save_file(self, source: Path, key: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str | None) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_url(self, key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, key: str) -> Path:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("非法存储路径")
        return path

    def save_stream(self, stream: BinaryIO, key: str, max_bytes: int | None = None) -> int:
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with target.open("wb") as output:
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    if max_bytes is not None and total > max_bytes:
                        raise ValueError("上传文件超过大小限制")
                    output.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return total

    def save_file(self, source: Path, key: str) -> int:
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target.stat().st_size

    def delete(self, key: str | None) -> None:
        if key:
            self.resolve(key).unlink(missing_ok=True)

    def get_url(self, key: str) -> str:
        return f"/storage/{key.replace(chr(92), '/')}"


class UnconfiguredObjectStorageBackend(StorageBackend):
    def _error(self) -> RuntimeError:
        return RuntimeError("S3/MinIO 存储尚未配置，请实现凭证与桶配置后启用")

    def save_stream(self, stream: BinaryIO, key: str, max_bytes: int | None = None) -> int:
        raise self._error()

    def save_file(self, source: Path, key: str) -> int:
        raise self._error()

    def delete(self, key: str | None) -> None:
        raise self._error()

    def get_url(self, key: str) -> str:
        raise self._error()

    def resolve(self, key: str) -> Path:
        raise self._error()


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_type == "local":
        return LocalStorageBackend(settings.storage_path)
    return UnconfiguredObjectStorageBackend()
