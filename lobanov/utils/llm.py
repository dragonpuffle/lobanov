"""Utility helpers for local Hugging Face causal-LM clinical extraction adapters.

Mirrors the layout and conventions of :mod:`lobanov.utils.stt`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import torch

from lobanov.infra.configs import NLPConfig
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


def safe_hf_dirname(model_id: str) -> str:
    """Sanitise a HF repo-id so it can be used as a directory name on any OS."""
    return re.sub(r'[<>:"/\\|?*]', "--", model_id).strip(".- ") or "model"


def safe_revision_dirname(revision: str) -> str:
    raw = revision.strip() or "default"
    return re.sub(r'[<>:"/\\|?*]', "_", raw) or "default"


def dir_has_model_weights(path: Path) -> bool:
    """Return True when *path* looks like a saved HF model directory."""
    if not path.is_dir():
        return False
    if not (path / "config.json").is_file():
        return False
    return bool(
        (path / "model.safetensors").is_file()
        or (path / "pytorch_model.bin").is_file()
        or (path / "model.safetensors.index.json").is_file()
        or (path / "pytorch_model.bin.index.json").is_file()
        or list(path.glob("*.safetensors"))
    )


def project_snapshot_dir(nlp: NLPConfig) -> Path:
    """Return the expected on-disk location for a downloaded NLP model."""
    root = Path(nlp.model_cache_dir).expanduser().resolve()
    return root / safe_hf_dirname(nlp.model) / safe_revision_dirname(nlp.revision)


def resolve_pretrained_source(nlp: NLPConfig) -> tuple[str, dict[str, Any]]:
    """Resolve where to load the model from.

    Priority:
    1. Explicit local directory (when ``nlp.model`` is an existing path with weights).
    2. Project snapshot directory (``models/nlp/<model-slug>/<revision>/``).
    3. Legacy flat directory (``models/nlp/<model-slug>/``).
    4. Hugging Face Hub with ``cache_dir`` pointing at the project cache root.
    """
    model_id = nlp.model.strip()
    explicit = Path(model_id).expanduser().resolve()
    if dir_has_model_weights(explicit):
        logger.info("load from explicit local dir {p!r}", p=str(explicit))
        return str(explicit), {}

    snap = project_snapshot_dir(nlp)
    if dir_has_model_weights(snap):
        logger.info("load from snapshot {p!r}", p=str(snap))
        return str(snap), {}

    legacy_flat = Path(nlp.model_cache_dir).expanduser().resolve() / safe_hf_dirname(model_id)
    if dir_has_model_weights(legacy_flat):
        logger.info("load from legacy cache dir {p!r}", p=str(legacy_flat))
        return str(legacy_flat), {}

    cache_dir = str(Path(nlp.model_cache_dir).expanduser().resolve())
    hub_kw: dict[str, Any] = {"cache_dir": cache_dir}
    if nlp.revision.strip():
        hub_kw["revision"] = nlp.revision.strip()
    logger.info("load from Hub {model!r} cache_dir={c!r}", model=model_id, c=cache_dir)
    return model_id, hub_kw


def pick_device_string(device: str) -> str:
    """Normalise device string; fall back to CPU when CUDA is unavailable."""
    d = device.lower().strip()
    if d == "auto":
        return "auto"
    if d.startswith("cuda") and torch.cuda.is_available():
        return device if ":" in device else "cuda:0"
    return "cpu"


def pick_torch_dtype(compute_type: str, device_str: str) -> torch.dtype | str:
    """Map a human-readable compute-type string to a :class:`torch.dtype`.

    Returns the string ``"auto"`` when ``compute_type="auto"`` so the caller can
    pass it directly to ``from_pretrained(torch_dtype="auto")``.
    """
    ct = compute_type.lower().strip()
    if ct == "auto":
        return "auto"
    cuda = device_str.startswith("cuda") or device_str == "auto"
    if ct in {"float16", "fp16", "half"}:
        return torch.float16
    if ct in {"bfloat16", "bf16", "bfp16"}:
        return torch.bfloat16 if (cuda and torch.cuda.is_bf16_supported()) else torch.float16
    return torch.float32
