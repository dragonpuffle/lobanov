from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast, override
from uuid import uuid4

import aiofiles.os
import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger
from lobanov.utils.stt import pick_device_string, resolve_pretrained_source

logger = get_logger(__name__)

_GRANITE_CARD_LANGUAGES = ["en", "en-US", "fr", "fr-FR", "de", "de-DE", "es", "es-ES", "pt", "pt-BR", "ja", "ja-JP"]
_GRANITE_INPUT_SAMPLE_RATE = 16_000


def _load_mono_16k(path: Path) -> torch.Tensor:
    wav, sr = torchaudio.load(str(path), normalize=True)
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != _GRANITE_INPUT_SAMPLE_RATE:
        wav = torchaudio.functional.resample(wav, sr, _GRANITE_INPUT_SAMPLE_RATE)
    return wav.cpu()


class GraniteSpeechSTTService(SpeechRecognitionProtocol):
    """IBM Granite Speech (``ibm-granite/granite-speech-4.1-2b``) via Transformers.

    English/French/German/Spanish/Portuguese/Japanese are listed on the model card; Russian is not officially
    supported — still usable as an experimental baseline for RU audio.
    """

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model_lock = asyncio.Lock()
        self._bundle: tuple[Any, Any] | None = None
        self._warned_ru_audio = False

    def _maybe_warn_about_russian(self, language: str) -> None:
        if language.lower().startswith("ru") and not self._warned_ru_audio:
            logger.warning(
                "Granite Speech: ru/ru-RU audio targets an unsupported language on the HF model card "
                "(English/French/German/Spanish/Portuguese/Japanese). Treat transcripts as exploratory only.",
            )
            self._warned_ru_audio = True

    def _granite_torch_dtype(self, *, cuda: bool) -> torch.dtype:
        ct = self._stt.compute_type.lower()
        if "bfloat16" in ct or ct in {"bf16", "bfp16"}:
            return torch.bfloat16 if cuda and torch.cuda.is_bf16_supported() else torch.float32
        if ct in {"float32", "fp32"}:
            return torch.float32
        return torch.bfloat16 if cuda and torch.cuda.is_bf16_supported() else torch.float16 if cuda else torch.float32

    def _load_sync(self) -> tuple[Any, Any]:
        source, from_pretrained_kw = resolve_pretrained_source(self._stt)
        device_str = pick_device_string(self._stt.device)

        processor: Any = AutoProcessor.from_pretrained(source, **from_pretrained_kw)
        cuda = device_str.startswith("cuda")
        dtype = self._granite_torch_dtype(cuda=cuda)

        if cuda:
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                source,
                device_map="auto",
                dtype=dtype,
                **from_pretrained_kw,
            )
        else:
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                source,
                dtype=dtype,
                **from_pretrained_kw,
            ).to("cpu")

        logger.info(
            "Loaded Granite Speech src={src!r} dtype={dt!s} cuda={cuda}",
            src=str(source),
            dt=str(dtype),
            cuda=cuda,
        )
        return processor, model

    async def _get_bundle(self) -> tuple[Any, Any]:
        if self._bundle is not None:
            return self._bundle
        async with self._model_lock:
            if self._bundle is None:
                self._bundle = await asyncio.to_thread(self._load_sync)
        return self._bundle

    def _infer_one_sync(self, path: Path, processor: Any, model: Any) -> str:
        device_torch = cast("torch.device", next(model.parameters()).device)

        wav = _load_mono_16k(path)

        tokenizer = processor.tokenizer
        user_prompt = "<|audio|>transcribe the speech with proper punctuation and capitalization."
        chat = [{"role": "user", "content": user_prompt}]
        prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

        raw_inputs = processor(prompt, wav, return_tensors="pt")
        inputs = raw_inputs.to(device_torch)

        beams = max(1, int(self._stt.beam_size))
        temperature = float(self._stt.temperature)

        forward = dict(inputs)

        gen_kwargs = {
            **forward,
            "max_new_tokens": 448,
            "num_beams": beams,
            "do_sample": temperature > 0,
        }
        if temperature > 0:
            gen_kwargs["temperature"] = temperature

        outputs = cast("torch.Tensor", model.generate(**gen_kwargs))

        input_ids = cast("torch.Tensor", forward["input_ids"])
        prompt_len = int(input_ids.shape[-1])
        continuation_ids = outputs[0, prompt_len:].detach().cpu()
        decoded = tokenizer.decode(continuation_ids, skip_special_tokens=True)
        return " ".join(decoded.split())

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        self._maybe_warn_about_russian(language)
        path_resolved = await asyncio.to_thread(lambda: Path(file_path).expanduser().resolve())
        if not await aiofiles.os.path.exists(str(path_resolved)):
            msg = f"Audio file not found: {path_resolved}"
            raise SpeechRecognitionError(msg)

        processor, model = await self._get_bundle()
        try:
            text = await asyncio.to_thread(self._infer_one_sync, path_resolved, processor, model)
            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=text,
                language=TranscriptLanguage.RU,
                confidence_score=0.75,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Granite Speech transcription failed")
            granite_exc_detail = str(e)
            granite_exc_msg = f"Granite Speech: {granite_exc_detail}"
            raise SpeechRecognitionError(granite_exc_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return sorted(set(_GRANITE_CARD_LANGUAGES))
