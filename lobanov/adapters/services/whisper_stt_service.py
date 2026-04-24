from datetime import UTC, datetime
from typing import override
from uuid import uuid4

import aiofiles.os
from faster_whisper import WhisperModel

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


class WhisperSTTService(SpeechRecognitionProtocol):
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def _parse_language(self, language: str) -> str:
        language_map = {
            "ru-RU": "ru",
            "ru": "ru",
        }
        return language_map.get(language, language[:2])

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        try:
            whisper_language = self._parse_language(language)

            segments, _ = self.model.transcribe(
                file_path, language=whisper_language, beam_size=5, vad_filter=True, word_timestamps=True
            )
            # faster-whisper returns a generator; we need a list for len() and multiple passes
            segments = list(segments)

            full_text = " ".join([segment.text for segment in segments])
            full_text = full_text.strip()

            avg_probability = 0.0
            confidence_score = 0.0
            if segments:
                total_prob = sum(segment.avg_logprob for segment in segments if segment.avg_logprob > 0)
                avg_probability = total_prob / len(segments) if segments else 0.0
                confidence_score = min(max(avg_probability, 0.0), 1.0)

            transcript_language = TranscriptLanguage.RU if whisper_language == "ru" else TranscriptLanguage.RU  # noqa: RUF034

            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=full_text,
                language=transcript_language,
                confidence_score=confidence_score,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.exception("Failed to transcribe audio")
            err_msg = f"Failed to transcribe audio: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return [
            "ru-RU",
            "ru",
        ]
