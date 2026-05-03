import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from transformers import AutoModelForCTC, AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

import lobanov.adapters.services.hf_stt_utils as _hf_stt_utils_side_effects  # noqa: F401
from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


class TransformersSTTService(SpeechRecognitionProtocol):
    """Local speech-to-text via Hugging Face transformers and torch."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model: Any = None
        self._processor: Any = None
        self._pipeline: Any = None
        self._model_lock = asyncio.Lock()

    @property
    def _cache_root(self) -> Path:
        return Path(self._stt.model_cache_dir).expanduser().resolve()

    @property
    def _model_dir(self) -> Path:
        safe_model_id = self._stt.model.replace("/", "--")
        return self._cache_root / safe_model_id

    def _model_is_downloaded(self) -> bool:
        model_dir = self._model_dir
        return (model_dir / "config.json").exists() and (
            (model_dir / "preprocessor_config.json").exists() or (model_dir / "processor_config.json").exists()
        )

    def _load_model_sync(self) -> None:
        model_is_downloaded = self._model_is_downloaded()
        model_source = str(self._model_dir) if model_is_downloaded else self._stt.model
        logger.info(
            "Loading transformers STT model {model!r} from {source!r}", model=self._stt.model, source=model_source
        )

        dtype = torch.float16 if self._stt.compute_type in {"float16", "fp16"} else torch.float32
        processor_kwargs: dict[str, Any] = {}
        model_kwargs: dict[str, Any] = {"dtype": dtype}
        revision = self._stt.revision.strip()
        if revision and not model_is_downloaded:
            processor_kwargs["revision"] = revision
            model_kwargs["revision"] = revision

        self._processor = AutoProcessor.from_pretrained(model_source, **processor_kwargs)
        try:
            self._model = AutoModelForSpeechSeq2Seq.from_pretrained(model_source, **model_kwargs)
        except ValueError:
            self._model = AutoModelForCTC.from_pretrained(model_source, **model_kwargs)

        if not model_is_downloaded:
            self._model_dir.mkdir(parents=True, exist_ok=True)
            self._processor.save_pretrained(self._model_dir)
            self._model.save_pretrained(self._model_dir)
            logger.info(
                "Saved transformers STT model {model!r} to {path}", model=self._stt.model, path=str(self._model_dir)
            )

        requested_device = self._stt.device.lower().strip()
        use_cuda = requested_device.startswith("cuda") and torch.cuda.is_available()
        if use_cuda:
            self._model = self._model.to(self._stt.device)
        elif requested_device.startswith("cuda"):
            logger.warning("CUDA was requested for transformers STT, but torch.cuda.is_available() is false; using CPU")

        self._apply_whisper_generation_config()

        device = -1
        if use_cuda:
            device = 0
            if ":" in requested_device:
                try:
                    device = int(requested_device.rsplit(":", maxsplit=1)[1])
                except ValueError:
                    logger.warning("Invalid CUDA device {device!r}; using cuda:0", device=self._stt.device)
        self._pipeline = pipeline(
            "automatic-speech-recognition",
            model=self._model,
            tokenizer=self._processor.tokenizer,
            feature_extractor=self._processor.feature_extractor,
            dtype=dtype,
            device=device,
        )

    async def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        async with self._model_lock:
            if self._pipeline is not None:
                return self._pipeline
            await asyncio.to_thread(self._load_model_sync)
        return self._pipeline

    def _parse_language(self, language: str) -> str:
        language_map = {
            "ru-RU": "russian",
            "ru": "russian",
        }
        return language_map.get(language, language[:2])

    def _is_whisper_model(self) -> bool:
        model_type = getattr(getattr(self._model, "config", None), "model_type", "")
        return "whisper" in str(model_type).lower() or "whisper" in self._stt.model.lower()

    def _apply_whisper_generation_config(self) -> None:
        """Whisper ``generate_with_fallback`` / ``_need_fallback`` in recent ``transformers`` builds is easy to
        break: (1) if only ``no_speech_threshold`` is set, ``logprobs`` may be undefined; (2) if ``logprob_threshold``
        is set (including a bogus ``-1.0`` workaround), the code may index ``seek_outputs[index][\"scores\"]`` even
        when ``seek_outputs[index]`` is a 1D token tensor from the pipeline. Disabling both thresholds avoids those
        branches; ``[stt] no_speech_threshold`` is therefore not applied to Whisper via ``generation_config`` here."""
        if not self._is_whisper_model() or self._model is None:
            return
        gc = self._model.generation_config
        gc.logprob_threshold = None
        gc.no_speech_threshold = None

    async def _transcribe(self, file_path: str, language: str) -> str:
        asr_pipeline = await self._get_pipeline()
        generate_kwargs: dict[str, object] = {}
        if self._is_whisper_model():
            generate_kwargs["task"] = "transcribe"
            generate_kwargs["language"] = self._parse_language(language)

        result = await asyncio.to_thread(
            asr_pipeline,
            file_path,
            generate_kwargs=generate_kwargs,
            return_timestamps=self._stt.word_timestamps,
        )
        if isinstance(result, dict):
            text = result.get("text", "")
            if isinstance(text, str):
                return text
        msg = f"Unexpected transformers STT result: {type(result).__name__}"
        raise SpeechRecognitionError(msg)

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        try:
            transcript_text = await self._transcribe(file_path, language)
            transcript_text = " ".join(transcript_text.split()).strip()

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
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Failed to transcribe audio with transformers")
            err_msg = f"Failed to transcribe audio with transformers: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
