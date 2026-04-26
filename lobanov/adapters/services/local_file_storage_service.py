import asyncio
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import override
from uuid import UUID

import aiofiles

from lobanov.infra.configs import StorageConfig
from lobanov.protocols.services.file_storage_protocol import FileStorageProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class FileStorageError(Exception):
    pass


class LocalFileStorageService(FileStorageProtocol):
    def __init__(self, storage_config: StorageConfig):
        self.audio_path = Path(storage_config.audio_path)
        self.documents_path = Path(storage_config.document_path)
        self.max_audio_size = storage_config.max_audio_size
        self.max_document_size = storage_config.max_document_size
        self.allowed_audio_formats: set[str] = {
            f".{ext.lower().lstrip('.')}" for ext in storage_config.allowed_audio_formats
        }
        self.allowed_document_formats: set[str] = {".txt", ".json", ".md", ".pdf", ".docx"}
        self.audio_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)

    def _validate_audio_file_size(self, file_size: int):
        if file_size > self.max_audio_size:
            err_msg = f"File size {file_size} exceeds maximum allowed size {self.max_audio_size}"
            raise FileStorageError(err_msg)

    def _validate_document_file_size(self, file_size: int):
        if file_size > self.max_document_size:
            err_msg = f"File size {file_size} exceeds maximum allowed size {self.max_document_size}"
            raise FileStorageError(err_msg)

    def _validate_audio_format(self, filename: str):
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_audio_formats:
            err_msg = f"Audio format {file_ext} is not allowed. Allowed formats: {self.allowed_audio_formats}"
            raise FileStorageError(err_msg)

    def _validate_document_format(self, filename: str):
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_document_formats:
            err_msg = f"Document format {file_ext} is not allowed. Allowed formats: {self.allowed_document_formats}"
            raise FileStorageError(err_msg)

    @override
    async def save_audio(self, file: BytesIO, filename: str, session_id: UUID) -> str:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        self._validate_audio_file_size(file_size)
        self._validate_audio_format(filename)

        session_dir = self.audio_path / str(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        file_path = session_dir / filename

        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file.getvalue())
        except Exception as e:
            logger.exception("Failed to save audio file")
            err_msg = f"Failed to save audio file: {e}"
            raise FileStorageError(err_msg) from e

        return str(file_path)

    @override
    async def get_audio_url(self, file_path: str) -> str:
        path = Path(file_path)
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"File not found: {file_path}"
            raise FileStorageError(err_msg)
        if not path.is_relative_to(self.audio_path):
            err_msg = f"File path is not within audio storage: {file_path}"
            raise FileStorageError(err_msg)
        return f"/api/v1/storage/audio/{path.relative_to(self.audio_path)}"

    @override
    async def delete_file(self, file_path: str) -> bool:
        if not await aiofiles.os.path.exists(file_path):
            return False

        try:
            if await aiofiles.os.path.isfile(file_path):
                await aiofiles.os.unlink(file_path)
            elif await aiofiles.os.path.isdir(file_path):
                await asyncio.to_thread(shutil.rmtree, file_path)
        except Exception as e:
            logger.exception("Failed to delete file {path}", path=file_path)
            err_msg = f"Failed to delete file {file_path}: {e}"
            raise FileStorageError(err_msg) from e
        else:
            return True

    @override
    async def save_document(self, content: str | bytes, filename: str, session_id: UUID) -> str:
        self._validate_document_format(filename)
        if isinstance(content, bytes):
            self._validate_document_file_size(len(content))
        else:
            self._validate_document_file_size(len(content.encode("utf-8")))

        session_dir = self.documents_path / str(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        file_path = session_dir / filename

        try:
            if isinstance(content, bytes):
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)
            else:
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)
        except Exception as e:
            logger.exception("Failed to save document")
            err_msg = f"Failed to save document: {e}"
            raise FileStorageError(err_msg) from e

        return str(file_path)
