from pydantic import BaseModel


class AudioFile(BaseModel):
    file_path: str
    file_name: str
    file_size: int
    format: str

    def get_file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)

    def __str__(self) -> str:
        return f"{self.file_name} ({self.format}, {self.get_file_size_mb():.2f} MB)"
