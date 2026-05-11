from __future__ import annotations

from typing import Any, override

from lobanov.adapters.services.stt.whisper_hf_stt_service import WhisperHFSTTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class RussianWhisperHFSTTService(WhisperHFSTTService):
    """Rus fine-tuned Whisper (e.g. ``dvislobokov/whisper-large-v3-turbo-russian``).

    Tries ``language=russian`` in ``generate_kwargs`` first; retries without ``language`` if generation fails.
    """

    def __init__(self, stt_config: STTConfig):
        super().__init__(stt_config)

    @override
    async def _execute_whisper(self, path_resolved: str, language: str) -> dict[str, Any]:
        primary_kw = self._whisper_generate_kwargs(language or "ru")
        try:
            return await self._run_whisper_pipe(path_resolved, primary_kw)
        except SpeechRecognitionError:
            raise
        except Exception as exc:
            if "language" not in primary_kw:
                ru_hf_detail = str(exc)
                ru_hf_msg = f"Russian Whisper HF: {ru_hf_detail}"
                raise SpeechRecognitionError(ru_hf_msg) from exc
            fallback_kw = dict(primary_kw)
            fallback_kw.pop("language", None)
            logger.warning(
                "Russian Whisper HF: forced language=russian failed; retry without language in generate_kwargs",
            )
            try:
                return await self._run_whisper_pipe(path_resolved, fallback_kw)
            except Exception as exc2:
                ru_hf_fb_detail = str(exc2)
                ru_hf_fb_msg = f"Russian Whisper HF (fallback): {ru_hf_fb_detail}"
                raise SpeechRecognitionError(ru_hf_fb_msg) from exc2
