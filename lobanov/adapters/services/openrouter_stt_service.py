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
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.audio_transcode import AudioTranscodeError, transcode_bytes_to_mp3
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

_OPENROUTER_CHAT_URL: Final[str] = "https://openrouter.ai/api/v1/chat/completions"
# Upstream (e.g. OpenAI via OpenRouter) often accepts only wav/mp3 in input_audio.format; see API error on m4a.
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


class SpeechRecognitionError(Exception):
    pass


def _message_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                t = part.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return "".join(parts)
    return str(content)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


class OpenRouterSTTService(SpeechRecognitionProtocol):
    """Speech-to-text via OpenRouter chat completions with input_audio (base64)."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config

    def _audio_format_for_path(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower().lstrip(".")
        fmt = _SUFFIX_TO_AUDIO_FORMAT.get(suffix)
        if fmt is None:
            err_msg = (
                f"Unsupported audio extension for OpenRouter STT: .{suffix or '(none)'}; "
                f"use one of: {', '.join(sorted(_SUFFIX_TO_AUDIO_FORMAT))}"
            )
            raise SpeechRecognitionError(err_msg)
        return fmt

    def _transcription_instruction(self, language: str) -> str:
        lang = language.lower().strip()
        lang_hint = "Russian" if lang.startswith("ru") else f"the language indicated ({language})"
        domain = self._stt.initial_prompt.strip()
        base = (
            f"Transcribe this audio verbatim in {lang_hint}. "
            "Output only the transcript text, no labels, no markdown, no commentary."
        )
        if domain:
            return f"{base}\n\nContext (terminology and style):\n{domain}"
        return base

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        if not self._stt.api_key.strip():
            raise SpeechRecognitionError("OpenRouter STT requires a non-empty api_key in [stt] config")

        source_format = self._audio_format_for_path(file_path)

        try:
            async with aiofiles.open(file_path, "rb") as audio_file:
                raw = await audio_file.read()
            if source_format in _OPENROUTER_NATIVE_FORMATS:
                audio_format = source_format
            else:
                try:
                    raw = await transcode_bytes_to_mp3(raw)
                except AudioTranscodeError as e:
                    raise SpeechRecognitionError(str(e)) from e
                audio_format = "mp3"
            b64_audio = base64.b64encode(raw).decode("ascii")

            headers = {
                "Authorization": f"Bearer {self._stt.api_key.strip()}",
                "Content-Type": "application/json",
                "X-Title": "Lobanov Clinical Documentation STT",
            }

            payload: dict[str, object] = {
                "model": self._stt.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._transcription_instruction(language)},
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": b64_audio,
                                    "format": audio_format,
                                },
                            },
                        ],
                    }
                ],
                "temperature": self._stt.temperature,
                "max_tokens": 16_384,
            }

            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
                response = await client.post(_OPENROUTER_CHAT_URL, headers=headers, json=payload)
                if response.is_error:
                    body = (response.text or "")[:8000]
                    log_msg = f"OpenRouter STT {response.status_code}: {body}"
                    logger.error(log_msg)
                    err_detail = body or response.reason_phrase
                    openrouter_err = f"OpenRouter STT rejected the request ({response.status_code}): {err_detail}"
                    raise SpeechRecognitionError(openrouter_err)
                result = response.json()

            raw_content = result["choices"][0]["message"]["content"]
            text_content = _message_content_to_text(raw_content)
            if not text_content.strip():
                err_msg = "OpenRouter STT returned empty transcript"
                raise SpeechRecognitionError(err_msg)

            full_text = " ".join(_strip_code_fences(text_content).split()).strip()

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
            logger.exception("Failed to transcribe audio via OpenRouter")
            err_msg = f"Failed to transcribe audio via OpenRouter: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
