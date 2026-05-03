import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, override
from uuid import uuid4

import aiofiles
import aiofiles.os
import httpx

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.audio_to_mp3 import AudioToMp3Error, convert_bytes_to_mp3
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

_OPENROUTER_TRANSCRIPTIONS_URL: Final[str] = "https://openrouter.ai/api/v1/audio/transcriptions"

_OPENROUTER_NATIVE_FORMATS: Final[frozenset[str]] = frozenset({"wav", "mp3"})

_SUFFIX_TO_AUDIO_FORMAT: Final[dict[str, str]] = {
    "wav": "wav",
    "mp3": "mp3",
    "m4a": "m4a",
    "ogg": "ogg",
    "flac": "flac",
    "aac": "aac",
    "aiff": "aiff",
    "aif": "aiff",
    "opus": "ogg",
}


class OpenRouterAudioSTTService(SpeechRecognitionProtocol):
    """Speech-to-text via OpenRouter audio transcriptions endpoint."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config

    def _audio_format_for_path(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower().lstrip(".")
        fmt = _SUFFIX_TO_AUDIO_FORMAT.get(suffix)
        if fmt is None:
            err_msg = (
                f"Unsupported audio extension for OpenRouter audio STT: .{suffix or '(none)'}; "
                f"use one of: {', '.join(sorted(_SUFFIX_TO_AUDIO_FORMAT))}"
            )
            raise SpeechRecognitionError(err_msg)
        return fmt

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        if not self._stt.api_key.strip():
            raise SpeechRecognitionError("OpenRouter audio STT requires a non-empty api_key in [stt] config")

        source_format = self._audio_format_for_path(file_path)

        try:
            async with aiofiles.open(file_path, "rb") as audio_file:
                raw = await audio_file.read()
            if source_format in _OPENROUTER_NATIVE_FORMATS:
                audio_format = source_format
            else:
                try:
                    raw = await convert_bytes_to_mp3(raw)
                except AudioToMp3Error as e:
                    raise SpeechRecognitionError(str(e)) from e
                audio_format = "mp3"
            b64_audio = base64.b64encode(raw).decode("ascii")

            headers = {
                "Authorization": f"Bearer {self._stt.api_key.strip()}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Lobanov Clinical Documentation STT",
            }

            payload: dict[str, object] = {
                "model": self._stt.model,
                "input_audio": {
                    "data": b64_audio,
                    "format": audio_format,
                },
            }

            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
                response = await client.post(_OPENROUTER_TRANSCRIPTIONS_URL, headers=headers, json=payload)
                if response.is_error:
                    body = (response.text or "")[:8000]
                    log_msg = f"OpenRouter audio STT {response.status_code}: {body}"
                    logger.error("{}", log_msg)  # noqa: PLE1205
                    err_detail = body or response.reason_phrase
                    openrouter_err = f"OpenRouter audio STT rejected the request ({response.status_code}): {err_detail}"
                    raise SpeechRecognitionError(openrouter_err)
                result = response.json()

            text_content = result.get("text", "")
            if not isinstance(text_content, str) or not text_content.strip():
                err_msg = "OpenRouter audio STT returned empty transcript"
                raise SpeechRecognitionError(err_msg)

            full_text = " ".join(text_content.split()).strip()

            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=full_text,
                language=TranscriptLanguage.RU,
                confidence_score=0.85,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Failed to transcribe audio via OpenRouter audio STT")
            err_msg = f"Failed to transcribe audio via OpenRouter audio STT: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
