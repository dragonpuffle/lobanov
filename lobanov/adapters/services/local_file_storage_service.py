import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import override
from uuid import UUID

from lobanov.protocols.services.file_storage_protocol import FileStorageProtocol


class FileStorageError(Exception):
    pass


class LocalFileStorageService(FileStorageProtocol):
    def __init__(self, base_path: str = "storage", max_file_size: int = 100 * 1024 * 1024):
        self.base_path = Path(base_path)
        self.max_file_size = max_file_size
        self.allowed_audio_formats: set[str] = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
        self.allowed_document_formats: set[str] = {".txt", ".json", ".md", ".pdf", ".docx"}
        self._ensure_directories()

    def _ensure_directories(self):
        self.audio_path = self.base_path / "audio"
        self.documents_path = self.base_path / "documents"
        self.audio_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)

    def _validate_file_size(self, file_size: int):
        if file_size > self.max_file_size:
            err_msg = f"File size {file_size} exceeds maximum allowed size {self.max_file_size}"
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

        self._validate_file_size(file_size)
        self._validate_audio_format(filename)

        session_dir = self.audio_path / str(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        file_path = session_dir / filename

        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file, f)
        except Exception as e:
            err_msg = f"Failed to save audio file: {e}"
            raise FileStorageError(err_msg) from e

        return str(file_path)

    @override
    async def get_audio_url(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            err_msg = f"File not found: {file_path}"
            raise FileStorageError(err_msg)
        if not path.is_relative_to(self.audio_path):
            err_msg = f"File path is not within audio storage: {file_path}"
            raise FileStorageError(err_msg)
        return f"/api/v1/storage/audio/{path.relative_to(self.audio_path)}"

    @override
    async def delete_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True  # noqa: TRY300
        except Exception as e:
            err_msg = f"Failed to delete file {file_path}: {e}"
            raise FileStorageError(err_msg) from e

    @override
    async def save_document(self, content: str, filename: str, session_id: UUID) -> str:
        self._validate_document_format(filename)

        session_dir = self.documents_path / str(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        file_path = session_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            err_msg = f"Failed to save document: {e}"
            raise FileStorageError(err_msg) from e

        return str(file_path)
