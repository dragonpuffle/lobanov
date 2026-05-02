import asyncio
import contextlib
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModel

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


def _revision_cache_dirname(revision: str | None) -> str:
    """Subdirectory under the model id for this Hub revision (branch/tag/commit)."""
    raw = (revision or "").strip()
    label = raw or "default"
    safe = re.sub(r'[<>:"/\\|?*]', "_", label)
    return safe or "default"


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

    @property
    def _cache_root(self) -> Path:
        return Path(self._stt.model_cache_dir).expanduser().resolve()

    @property
    def _model_dir(self) -> Path:
        safe_model_id = self._stt.model.replace("/", "--")
        return self._cache_root / safe_model_id / _revision_cache_dirname(self._revision)

    def _local_snapshot_has_weights(self, model_dir: Path) -> bool:
        if not (model_dir / "config.json").is_file():
            return False
        return bool(
            (model_dir / "model.safetensors").is_file()
            or (model_dir / "pytorch_model.bin").is_file()
            or (model_dir / "model.safetensors.index.json").is_file()
            or any(model_dir.glob("*.safetensors"))
        )

    def _ensure_local_snapshot(self, model_dir: Path) -> None:
        if self._local_snapshot_has_weights(model_dir):
            return
        model_dir.mkdir(parents=True, exist_ok=True)
        rev_label = self._revision if self._revision is not None else "default"
        logger.info(
            "Downloading GigaAM snapshot {model!r} revision {rev!r} into {path}",
            model=self._stt.model,
            rev=rev_label,
            path=str(model_dir),
        )
        snapshot_download(
            repo_id=self._stt.model,
            revision=self._revision,
            local_dir=str(model_dir),
        )

    def _load_model_sync(self) -> Any:
        model_dir = self._model_dir
        self._ensure_local_snapshot(model_dir)
        logger.info("Loading GigaAM from {path}", path=str(model_dir))
        with _cpu_default_device_guard():
            model = _gigaam_from_pretrained(str(model_dir))
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
