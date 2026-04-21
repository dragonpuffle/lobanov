import re

from pydantic import BaseModel


class TranscriptText(BaseModel):
    text: str

    def word_count(self) -> int:
        return len(self.text.split())

    def character_count(self) -> int:
        return len(self.text)

    def sentence_count(self) -> int:
        sentences = re.split(r"[.!?]+", self.text)
        return len([s for s in sentences if s.strip()])

    def contains_text(self, search_text: str, case_sensitive: bool = False) -> bool:  # noqa: FBT001, FBT002
        if not case_sensitive:
            return search_text.lower() in self.text.lower()
        return search_text in self.text

    def get_excerpt(self, max_length: int = 200) -> str:
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length].rsplit(" ", 1)[0] + "..."

    def __str__(self) -> str:
        return self.text
