from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from transformers import AutoModel

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger
from lobanov.utils.stt import dir_has_model_weights, pick_device_string, resolve_pretrained_source

logger = get_logger(__name__)


def resolve_device_for_giga(stt: STTConfig) -> torch.device:
    device_str = pick_device_string(stt.device)
    if device_str.startswith("cuda") and torch.cuda.is_available():
        return torch.device(device_str)
    return torch.device("cpu")


class GigaAMSTTService(SpeechRecognitionProtocol):
    """GigaAM v3 remote-code hub model (``ai-sage/GigaAM-v3``) with selectable ``revision`` head."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model_lock = asyncio.Lock()
        self._model: Any | None = None

    def _load_sync(self) -> Any:
        source, from_pretrained_kw = resolve_pretrained_source(self._stt)
        p = Path(source).expanduser().resolve()

        kwa = dict(from_pretrained_kw)
        if not (p.is_dir() and dir_has_model_weights(p)):
            rev = self._stt.revision.strip() or "e2e_rnnt"
            kwa.setdefault("revision", rev)

        logger.info("Loading GigaAM from {src!r} kwa={kw!r}", src=str(source), kw=kwa)

        model = AutoModel.from_pretrained(
            source,
            trust_remote_code=True,
            **kwa,
        )
        model.to(resolve_device_for_giga(self._stt))
        logger.info(
            "GigaAM weights loaded revision={rw!s}",
            rw=str(kwa.get("revision", "")),
        )
        return model

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._model_lock:
            if self._model is None:
                self._model = await asyncio.to_thread(self._load_sync)
        return self._model

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        _ = language
        path_resolved = await asyncio.to_thread(lambda: str(Path(file_path).expanduser().resolve()))
        if not await aiofiles.os.path.exists(path_resolved):
            giga_miss_msg = f"Audio file not found: {path_resolved}"
            raise SpeechRecognitionError(giga_miss_msg)

        model = await self._get_model()
        try:
            raw = await asyncio.to_thread(model.transcribe, path_resolved)
            text = " ".join(str(raw).strip().split())
            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=text,
                language=TranscriptLanguage.RU,
                confidence_score=0.8,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("GigaAM transcription failed")
            giga_exc_detail = str(e)
            giga_exc_msg = f"GigaAM: {giga_exc_detail}"
            raise SpeechRecognitionError(giga_exc_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru", "ru-RU"]
