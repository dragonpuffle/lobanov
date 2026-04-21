import re
from typing import override

from lobanov.protocols import TextProcessingProtocol


class TextProcessingError(Exception):
    pass


class TextPreprocessingService(TextProcessingProtocol):
    def __init__(self, lowercase: bool = True, remove_special_chars: bool = True):  # noqa: FBT001, FBT002
        self.lowercase = lowercase
        self.remove_special_chars = remove_special_chars

    @override
    async def preprocess_text(self, text: str) -> str:
        try:
            if not text:
                return text

            cleaned = await self.clean_text(text)
            return await self.normalize_text(cleaned)
        except Exception as e:
            err_msg = f"Failed to preprocess text: {e}"
            raise TextProcessingError(err_msg) from e

    @override
    async def clean_text(self, text: str) -> str:
        try:
            if not text:
                return text

            cleaned = text

            if self.lowercase:
                cleaned = cleaned.lower()

            if self.remove_special_chars:
                cleaned = re.sub(r'[^\w\s\.,!?;:\-\'"()]', "", cleaned)

            cleaned = re.sub(r"\s+", " ", cleaned)
            return cleaned.strip()
        except Exception as e:
            err_msg = f"Failed to clean text: {e}"
            raise TextProcessingError(err_msg) from e

    @override
    async def normalize_text(self, text: str) -> str:
        try:
            if not text:
                return text

            normalized = text

            normalized = re.sub(r"\s+([.,!?;:])", r"\1", normalized)

            normalized = re.sub(r"\.{2,}", ".", normalized)
            normalized = re.sub(r"\?{2,}", "?", normalized)
            normalized = re.sub(r"!{2,}", "!", normalized)

            normalized = re.sub(r"([.,!?;:])\1+", r"\1", normalized)

            normalized = re.sub(r"\s+", " ", normalized)
            return normalized.strip()
        except Exception as e:
            err_msg = f"Failed to normalize text: {e}"
            raise TextProcessingError(err_msg) from e
