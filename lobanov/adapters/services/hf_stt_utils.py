from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import torch
import transformers.utils.import_utils as _transformers_import_utils

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig


def sync_transformers_torchcodec_flag_with_importability() -> None:
    """``pyannote-audio`` installs ``torchcodec``; ``transformers`` only checks that the dist is present, then
    ``import torchcodec`` runs during ASR preprocessing and can fail on Windows (native DLL / FFmpeg shared).
    If import does not work, report torchcodec as unavailable so the pipeline falls back to ``ffmpeg_read``."""
    try:
        import torchcodec  # noqa: F401, PLC0415
    except Exception:

        def _no_torchcodec() -> bool:
            return False

        _transformers_import_utils.is_torchcodec_available = _no_torchcodec  # type: ignore[method-assign]
        import transformers.utils as _transformers_utils  # noqa: PLC0415

        _transformers_utils.is_torchcodec_available = _no_torchcodec  # type: ignore[method-assign]


sync_transformers_torchcodec_flag_with_importability()


def safe_hf_dirname(model_id: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "--", model_id).strip(".- ") or "model"


def safe_revision_dirname(revision: str | None) -> str:
    raw = (revision or "").strip() or "default"
    safe = re.sub(r'[<>:"/\\|?*]', "_", raw)
    return safe or "default"


def get_hf_model_dir_with_revision(config: STTConfig) -> Path:
    root = Path(config.model_cache_dir).expanduser().resolve()
    return root / safe_hf_dirname(config.model) / safe_revision_dirname(config.revision)


def has_hf_snapshot_weights(model_dir: Path) -> bool:
    if not (model_dir / "config.json").is_file():
        return False
    return bool(
        (model_dir / "model.safetensors").is_file()
        or (model_dir / "pytorch_model.bin").is_file()
        or (model_dir / "model.safetensors.index.json").is_file()
        or (model_dir / "pytorch_model.bin.index.json").is_file()
        or bool(list(model_dir.glob("*.safetensors")))
    )


def ensure_hf_snapshot(
    config: STTConfig,
    *,
    revision: str | None = None,
    allow_patterns: list[str] | None = None,
) -> Path:
    """Download revision into ``model_cache_dir / safe(model) / safe(revision)`` if weights are missing."""
    from huggingface_hub import snapshot_download  # noqa: PLC0415

    model_dir = get_hf_model_dir_with_revision(config)
    if has_hf_snapshot_weights(model_dir):
        return model_dir
    model_dir.mkdir(parents=True, exist_ok=True)
    rev_arg = revision if revision is not None else (config.revision.strip() or None)
    snapshot_download(
        repo_id=config.model,
        revision=rev_arg,
        local_dir=str(model_dir),
        allow_patterns=allow_patterns,
    )
    return model_dir


def torch_dtype_from_stt_config(config: STTConfig, *, default: torch.dtype = torch.float32) -> torch.dtype:
    value = config.compute_type.lower().strip()
    if value in {"float16", "fp16"}:
        return torch.float16
    if value in {"bfloat16", "bf16"}:
        return torch.bfloat16
    if value in {"float32", "fp32"}:
        return torch.float32
    return default


def normalize_transcript_text(text: str) -> str:
    return " ".join(text.split()).strip()


def resolve_audio_path_str(file_path: str) -> str:
    """Normalize path in a blocking call; wrap with ``asyncio.to_thread`` from async adapters (ASYNC240)."""
    return str(Path(file_path).expanduser().resolve())


def build_transcript_from_text(text: str) -> Transcript:
    return Transcript(
        id=uuid4(),
        session_id=uuid4(),
        audio_record_id=uuid4(),
        text=normalize_transcript_text(text),
        language=TranscriptLanguage.RU,
        confidence_score=0.8,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def pipeline_device_number(stt_device: str) -> int | str:
    """Map ``STTConfig.device`` like ``cuda`` or ``cuda:1`` to ``pipeline(..., device=...)``."""
    req = stt_device.lower().strip()
    if not req.startswith("cuda") or not torch.cuda.is_available():
        return -1
    if ":" not in req:
        return 0
    try:
        return int(req.rsplit(":", maxsplit=1)[1])
    except ValueError:
        return 0


def whisper_parse_language(language: str) -> str:
    language_map = {
        "ru-RU": "russian",
        "ru": "russian",
    }
    return language_map.get(language, language[:2] if language else "")
