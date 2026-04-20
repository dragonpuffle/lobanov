from pathlib import Path
from typing import Final


class AudioFile:
    SUPPORTED_FORMATS: Final[set[str]] = {
        "mp3", "wav", "m4a", "flac", "aac", "ogg", "wma"
    }

    MAX_FILE_SIZE: Final[int] = 100 * 1024 * 1024

    def __init__(self, file_path: str, file_name: str, file_size: int, format: str) -> None:
        self._validate_file_name(file_name)
        self._validate_file_size(file_size)
        self._validate_format(format)
        self._validate_file_path(file_path)

        self._file_path = file_path
        self._file_name = file_name
        self._file_size = file_size
        self._format = format.lower()

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_name(self) -> str:
        return self._file_name

    @property
    def file_size(self) -> int:
        return self._file_size

    @property
    def format(self) -> str:
        return self._format

    def _validate_file_name(self, file_name: str) -> None:
        if not file_name:
            raise ValueError("File name cannot be empty")
        if len(file_name) > 255:
            raise ValueError("File name exceeds maximum length of 255 characters")
        invalid_chars = '<>:"/\\|?*'
        if any(char in file_name for char in invalid_chars):
            raise ValueError(f"File name contains invalid characters: {invalid_chars}")

    def _validate_file_size(self, file_size: int) -> None:
        if file_size <= 0:
            raise ValueError("File size must be greater than 0")
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum allowed size of "
                f"{self.MAX_FILE_SIZE / (1024 * 1024):.0f} MB"
            )

    def _validate_format(self, format: str) -> None:
        if not format:
            raise ValueError("Audio format cannot be empty")
        if format.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {format}. "
                f"Supported formats: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

    def _validate_file_path(self, file_path: str) -> None:
        if not file_path:
            raise ValueError("File path cannot be empty")
        try:
            Path(file_path)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid file path: {e}") from e

    def get_file_size_mb(self) -> float:
        return self._file_size / (1024 * 1024)

    def __str__(self) -> str:
        return f"{self._file_name} ({self._format}, {self.get_file_size_mb():.2f} MB)"

    def __repr__(self) -> str:
        return (
            f"AudioFile(file_path={self._file_path!r}, file_name={self._file_name!r}, "
            f"file_size={self._file_size}, format={self._format!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AudioFile):
            return NotImplemented
        return (
            self._file_path == other._file_path
            and self._file_name == other._file_name
        )

    def __hash__(self) -> int:
        return hash((self._file_path, self._file_name))
