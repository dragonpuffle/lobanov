import re
from pathlib import Path
from typing import Any

import torch

from lobanov.infra.configs import STTConfig
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


def safe_hf_dirname(model_id: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "--", model_id).strip(".- ") or "model"


def safe_revision_dirname(revision: str) -> str:
    raw = revision.strip() or "default"
    return re.sub(r'[<>:"/\\|?*]', "_", raw) or "default"


def dir_has_model_weights(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / "config.json").is_file():
        return False
    return bool(
        (path / "model.safetensors").is_file()
        or (path / "pytorch_model.bin").is_file()
        or (path / "model.safetensors.index.json").is_file()
        or (path / "pytorch_model.bin.index.json").is_file()
        or bool(list(path.glob("*.safetensors")))
    )


def project_snapshot_dir(stt: STTConfig) -> Path:
    """Same layout as ``snapshot_download(..., local_dir=...)`` / other STT adapters."""
    root = Path(stt.model_cache_dir).expanduser().resolve()
    return root / safe_hf_dirname(stt.model) / safe_revision_dirname(stt.revision)


def resolve_pretrained_source(stt: STTConfig) -> tuple[str, dict[str, Any]]:
    """Prefer on-disk folder over Hub: explicit path, then project snapshot dir, else repo id + cache_dir."""
    model_id = stt.model.strip()
    explicit = Path(model_id).expanduser().resolve()
    if dir_has_model_weights(explicit):
        logger.info("load from explicit local dir {p!r}", p=str(explicit))
        return str(explicit), {}

    snap = project_snapshot_dir(stt)
    if dir_has_model_weights(snap):
        logger.info("load from snapshot {p!r}", p=str(snap))
        return str(snap), {}

    legacy_flat = Path(stt.model_cache_dir).expanduser().resolve() / safe_hf_dirname(stt.model)
    if dir_has_model_weights(legacy_flat):
        logger.info("load from legacy cache dir {p!r}", p=str(legacy_flat))
        return str(legacy_flat), {}

    cache_dir = str(Path(stt.model_cache_dir).expanduser().resolve())
    hub_kw: dict[str, Any] = {"cache_dir": cache_dir}
    if stt.revision.strip():
        hub_kw["revision"] = stt.revision.strip()
    logger.info("load from Hub {model!r} cache_dir={c!r}", model=model_id, c=cache_dir)
    return model_id, hub_kw


def pick_device_string(stt_device: str) -> str:
    if stt_device.lower().strip().startswith("cuda") and torch.cuda.is_available():
        return stt_device if ":" in stt_device else "cuda:0"
    return "cpu"


def language_for_whisper(language: str) -> str:
    return {"ru": "russian", "ru-RU": "russian"}.get(language, language[:2] if language else "russian")
