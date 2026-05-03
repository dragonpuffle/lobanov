"""Russian fine-tuned Whisper (e.g. dvislobokov/whisper-large-v3-turbo-russian)."""

from __future__ import annotations

from typing import Any, override

from lobanov.adapters.services.whisper_hf_stt_service import WhisperHFSTTService


class RussianWhisperHFSTTService(WhisperHFSTTService):
    """Same pipeline path as Whisper; defaults language to Russian in ``generate_kwargs``."""

    @override
    def _generate_kwargs(self, language: str) -> dict[str, Any]:
        base = super()._generate_kwargs(language)
        base["language"] = "russian"
        base["task"] = "transcribe"
        return base
