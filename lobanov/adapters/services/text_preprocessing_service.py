import re
from typing import override

from lobanov.infra.configs import TextPreprocessingConfig
from lobanov.protocols import TextProcessingProtocol
from lobanov.utils.clinical_normalization import safe_normalize_transcript
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class TextProcessingError(Exception):
    pass


class TextPreprocessingService(TextProcessingProtocol):
    def __init__(self, text_preprocessing_config: TextPreprocessingConfig):
        self.lowercase = text_preprocessing_config.lowercase
        self.remove_special_chars = text_preprocessing_config.remove_special_chars

    @override
    async def preprocess_text(self, text: str) -> str:
        try:
            if not text:
                return text

            cleaned = await self.clean_text(text)
            normalized = await self.normalize_text(cleaned)
            return safe_normalize_transcript(normalized)
        except Exception as e:
            logger.exception("Failed to preprocess text")
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
            logger.exception("Failed to clean text")
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
            logger.exception("Failed to normalize text")
            err_msg = f"Failed to normalize text: {e}"
            raise TextProcessingError(err_msg) from e
