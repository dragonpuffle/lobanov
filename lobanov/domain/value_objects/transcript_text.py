import re
from typing import Final


class TranscriptText:
    MAX_LENGTH: Final[int] = 1_000_000

    MIN_LENGTH: Final[int] = 10

    REPEATED_CHAR_PATTERN: Final[re.Pattern[str]] = re.compile(r'(.)\1{10,}')

    def __init__(self, text: str) -> None:
        self._validate_text(text)
        self._text = text.strip()

    @property
    def text(self) -> str:
        return self._text

    def _validate_text(self, text: str) -> None:
        if not text:
            raise ValueError("Transcript text cannot be empty")

        stripped_text = text.strip()
        if len(stripped_text) < self.MIN_LENGTH:
            raise ValueError(
                f"Transcript text must be at least {self.MIN_LENGTH} characters long"
            )
        if len(stripped_text) > self.MAX_LENGTH:
            raise ValueError(
                f"Transcript text exceeds maximum length of {self.MAX_LENGTH} characters"
            )

        if self.REPEATED_CHAR_PATTERN.search(stripped_text):
            raise ValueError(
                "Transcript text contains excessive repeated characters, "
                "which may indicate a transcription error"
            )

    def word_count(self) -> int:
        return len(self._text.split())

    def character_count(self) -> int:
        return len(self._text)

    def sentence_count(self) -> int:
        sentences = re.split(r'[.!?]+', self._text)
        return len([s for s in sentences if s.strip()])

    def contains_text(self, search_text: str, case_sensitive: bool = False) -> bool:
        if not case_sensitive:
            return search_text.lower() in self._text.lower()
        return search_text in self._text

    def get_excerpt(self, max_length: int = 200) -> str:
        if len(self._text) <= max_length:
            return self._text
        return self._text[:max_length].rsplit(' ', 1)[0] + '...'

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        excerpt = self.get_excerpt(50)
        return f"TranscriptText(text={excerpt!r}...)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TranscriptText):
            return NotImplemented
        return self._text.lower() == other._text.lower()

    def __hash__(self) -> int:
        return hash(self._text.lower())
