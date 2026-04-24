import asyncio
from datetime import UTC, datetime
from typing import Any, override
from uuid import uuid4

import aiofiles.os
from transformers import AutoModel

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


class GigaAMSTTService(SpeechRecognitionProtocol):
    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        rev = stt_config.revision.strip()
        self._revision: str | None = rev or None
        self._model: Any = None
        self._model_lock = asyncio.Lock()

    def _load_model_sync(self) -> Any:
        kwargs: dict[str, Any] = {"trust_remote_code": True}
        if self._revision is not None:
            kwargs["revision"] = self._revision
        model = AutoModel.from_pretrained(self._stt.model, **kwargs)
        if hasattr(model, "to"):
            model = model.to(self._stt.device)
        return model

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._model_lock:
            if self._model is not None:
                return self._model
            logger.info("Loading GigaAM model {model!r}; first run may download weights", model=self._stt.model)
            self._model = await asyncio.to_thread(self._load_model_sync)
        return self._model

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        try:
            await self._get_model()
            transcript_text = await asyncio.to_thread(self._run_inference, file_path)
            transcript_text = " ".join(transcript_text.split())

            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=transcript_text,
                language=TranscriptLanguage.RU,
                confidence_score=0.8,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.exception("Failed to transcribe audio with GigaAM")
            err_msg = f"Failed to transcribe audio with GigaAM: {e}"
            raise SpeechRecognitionError(err_msg) from e

    def _run_inference(self, file_path: str) -> str:
        # GigaAM API differs by revision, so we probe common method names.
        model = self._model
        for method_name in ("transcribe", "transcribe_file", "asr"):
            method = getattr(model, method_name, None)
            if callable(method):
                result = method(file_path)
                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    text = result.get("text", "")
                    if isinstance(text, str):
                        return text
                if isinstance(result, list) and result and isinstance(result[0], dict):
                    text = result[0].get("text", "")
                    if isinstance(text, str):
                        return text

        msg = "Unsupported GigaAM model API. Expected one of methods: transcribe, transcribe_file, asr"
        raise SpeechRecognitionError(msg)

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
