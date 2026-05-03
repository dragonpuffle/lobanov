from __future__ import annotations

import asyncio
from typing import Any, override

import aiofiles.os
import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

import lobanov.adapters.services.hf_stt_utils as _hf_stt_utils_side_effects  # noqa: F401
from lobanov.adapters.services.hf_stt_utils import (
    build_transcript_from_text,
    ensure_hf_snapshot,
    resolve_audio_path_str,
    torch_dtype_from_stt_config,
)
from lobanov.domain.entities.transcript import Transcript
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

GRANITE_ASR_PROMPT = "<|audio|>transcribe the speech with proper punctuation and capitalization."


class SpeechRecognitionError(Exception):
    pass


def _mono_16k_wav(audio_path: str) -> tuple[torch.Tensor, int]:
    wav, sr = torchaudio.load(audio_path, normalize=True)
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    target_sr = 16000
    if sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
    return wav, target_sr


class GraniteSpeechSTTService(SpeechRecognitionProtocol):
    """``ibm-granite/granite-speech-4.1-2b`` style multimodal seq2seq (English prompt required per model card)."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model: Any = None
        self._processor: Any = None
        self._tokenizer: Any = None
        self._model_lock = asyncio.Lock()

    def _resolve_torch_device(self) -> torch.device:
        req = self._stt.device.lower().strip()
        if req.startswith("cuda") and torch.cuda.is_available():
            return torch.device(self._stt.device)
        return torch.device("cpu")

    def _load_model_sync(self) -> None:
        local_dir = str(ensure_hf_snapshot(self._stt))
        logger.info("Loading Granite Speech from {dir!r}", dir=local_dir)
        dt = torch_dtype_from_stt_config(self._stt, default=torch.float32)

        torch_device = self._resolve_torch_device()
        processor = AutoProcessor.from_pretrained(local_dir)
        tokenizer = processor.tokenizer

        load_kwargs: dict[str, Any] = {"dtype": dt}
        if torch_device.type == "cuda":
            load_kwargs["device_map"] = str(torch_device)

        try:
            model = AutoModelForSpeechSeq2Seq.from_pretrained(local_dir, **load_kwargs)
        except Exception:
            logger.exception("Granite Speech from_pretrained failed; retrying without device_map")
            model = AutoModelForSpeechSeq2Seq.from_pretrained(local_dir, dtype=dt)

        self._processor = processor
        self._tokenizer = tokenizer
        self._model = model.to(torch_device)

    async def _get_stack(self) -> tuple[Any, Any, Any]:
        if self._model is not None and self._processor is not None and self._tokenizer is not None:
            return self._model, self._processor, self._tokenizer
        async with self._model_lock:
            if self._model is not None and self._processor is not None and self._tokenizer is not None:
                return self._model, self._processor, self._tokenizer
            await asyncio.to_thread(self._load_model_sync)
        return self._model, self._processor, self._tokenizer

    def _infer_sync(self, audio_path: str) -> str:
        model = self._model
        processor = self._processor
        tokenizer = self._tokenizer
        if model is None or processor is None or tokenizer is None:
            msg = "Granite Speech model not loaded"
            raise SpeechRecognitionError(msg)

        torch_device = next(model.parameters()).device
        dev_str = "cuda" if torch_device.type == "cuda" else "cpu"

        wav, _sr_actual = _mono_16k_wav(audio_path)

        chat = [{"role": "user", "content": GRANITE_ASR_PROMPT}]
        prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

        model_inputs = processor(prompt, wav, device=dev_str, return_tensors="pt").to(torch_device)

        beams = max(1, self._stt.beam_size)
        model_outputs = model.generate(
            **model_inputs,
            max_new_tokens=448,
            do_sample=self._stt.temperature > 0,
            temperature=self._stt.temperature if self._stt.temperature > 0 else None,
            num_beams=beams,
        )

        num_input_tokens = model_inputs["input_ids"].shape[-1]
        new_tokens = model_outputs[:, num_input_tokens:]
        texts = tokenizer.batch_decode(new_tokens, add_special_tokens=False, skip_special_tokens=True)
        if not texts:
            msg = "Granite Speech returned empty decoding"
            raise SpeechRecognitionError(msg)
        return texts[0]

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        del language
        path_str = await asyncio.to_thread(resolve_audio_path_str, file_path)
        if not await aiofiles.os.path.exists(path_str):
            err_msg = f"Audio file not found: {path_str}"
            raise SpeechRecognitionError(err_msg)

        try:
            await self._get_stack()
            text = await asyncio.to_thread(self._infer_sync, path_str)
            return build_transcript_from_text(text)
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Failed to transcribe audio with Granite Speech")
            msg = f"Failed to transcribe audio with Granite Speech: {e}"
            raise SpeechRecognitionError(msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        logger.warning(
            "Granite Speech 4.1-2b card lists EN/FR/DE/ES/PT/JA training focus; ru is experimental.",
        )
        return ["ru-RU", "ru"]
