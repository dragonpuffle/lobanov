import asyncio
import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from transformers import AutoModel

from lobanov.adapters.services.hf_stt_utils import (
    ensure_hf_snapshot,
    get_hf_model_dir_with_revision,
    has_hf_snapshot_weights,
)
from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


@torch.compiler.disable
def _gigaam_from_pretrained(local_dir: str) -> Any:
    """Load hub snapshot; decorator avoids dynamo on ``torch.max`` in torchaudio (CM form conflicts in-thread)."""
    return AutoModel.from_pretrained(
        local_dir,
        trust_remote_code=True,
        low_cpu_mem_usage=False,
    )


@contextlib.contextmanager
def _cpu_default_device_guard() -> Iterator[None]:
    """Force ``torch.zeros`` etc. to CPU during GigaAM/torchaudio Mel init (hub code uses default device)."""
    try:
        prev_default = torch.get_default_device()
    except Exception:
        prev_default = None
    torch.set_default_device("cpu")
    try:
        yield
    finally:
        if prev_default is not None:
            with contextlib.suppress(Exception):
                torch.set_default_device(prev_default)


class GigaAMSTTService(SpeechRecognitionProtocol):
    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        rev = stt_config.revision.strip()
        self._revision: str | None = rev or None
        self._model: Any = None
        self._model_lock = asyncio.Lock()

    def _maybe_log_download_start(self, model_dir: Path) -> None:
        if has_hf_snapshot_weights(model_dir):
            return
        rev_label = self._revision if self._revision is not None else "default"
        logger.info(
            "Downloading GigaAM snapshot {model!r} revision {rev!r} into {path}",
            model=self._stt.model,
            rev=rev_label,
            path=str(model_dir),
        )

    def _load_model_sync(self) -> Any:
        model_dir = get_hf_model_dir_with_revision(self._stt)
        self._maybe_log_download_start(model_dir)
        local_dir_path = ensure_hf_snapshot(self._stt)
        local_dir_str = str(local_dir_path)
        logger.info("Loading GigaAM from {path}", path=local_dir_str)
        with _cpu_default_device_guard():
            model = _gigaam_from_pretrained(local_dir_str)
        if hasattr(model, "to"):
            model = model.to(self._stt.device)
        return model

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._model_lock:
            if self._model is not None:
                return self._model
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
