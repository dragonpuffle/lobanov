# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from lobanov.compat.transformers_asr_no_torchcodec import disable_torchcodec_probe_for_asr

disable_torchcodec_probe_for_asr()

from lobanov.adapters.services.stt.gigaam_stt_service import GigaAMSTTService
from lobanov.adapters.services.stt.granite_speech_stt_service import GraniteSpeechSTTService
from lobanov.adapters.services.stt.openrouter_audio_service import OpenRouterAudioService
from lobanov.adapters.services.stt.openrouter_audio_stt_service import OpenRouterAudioSTTService
from lobanov.adapters.services.stt.russian_whisper_hf_stt_service import RussianWhisperHFSTTService
from lobanov.adapters.services.stt.vibevoice_asr_stt_service import VibeVoiceHFSTTService
from lobanov.adapters.services.stt.whisper_hf_stt_service import WhisperHFSTTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol

load_dotenv()
# Supported: whisper_hf, russian_whisper_hf, granite_speech_hf, gigaam_hf, vibevoice_hf,
# openrouter_audio, openrouter_audio_stt
BACKEND = "whisper_hf"

AUDIO_1 = Path(r"experiments/audio/диалог-1-реал.mp3")
AUDIO_2 = Path(r"experiments/audio/диалог-15-эмиль.mp3")

LANG = "ru"


def build_stt_config() -> STTConfig:  # noqa: PLR0911
    common = {
        "language": LANG,
        "beam_size": 5,
        "vad_filter": True,
        "word_timestamps": True,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "condition_on_previous_text": True,
        "initial_prompt": "",
    }

    cache = "models/stt"

    if BACKEND == "openrouter_audio_stt":
        return STTConfig(
            provider="openrouter_audio_stt",
            model="openai/whisper-large-v3-turbo",
            api_key=os.environ["OPENROUTER_API_KEY"],
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    if BACKEND == "openrouter_audio":
        return STTConfig(
            provider="openrouter_audio",
            model="openai/gpt-audio-mini",
            api_key=os.environ["OPENROUTER_API_KEY"],
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    # OpenAI Whisper large v3 family (HF card uses torch_dtype + pipeline ASR recipe).
    if BACKEND == "whisper_hf":
        # openai/whisper-medium
        # openai/whisper-large-v3-turbo
        # openai/whisper-large-v3
        # openai/whisper-base

        return STTConfig(
            provider="whisper_hf",
            model="openai/whisper-large-v3-turbo",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    # Rus FT checkpoint (still Hugging Face SpeechSeq2Seq + ASR pipeline under the hood).
    if BACKEND == "russian_whisper_hf":
        return STTConfig(
            provider="russian_whisper_hf",
            model="dvislobokov/whisper-large-v3-turbo-russian",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    # IBM Granite (card languages exclude Russian — useful only as exploratory RU baseline).
    if BACKEND == "granite_speech_hf":
        return STTConfig(
            provider="granite_speech_hf",
            model="ibm-granite/granite-speech-4.1-2b",
            api_key="",
            device="cuda",
            revision="",
            compute_type="bfloat16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "gigaam_hf":
        # ``revision`` selects GigaAM head: ssl | ctc | rnnt | e2e_ctc | e2e_rnnt
        return STTConfig(
            provider="gigaam_hf",
            model="ai-sage/GigaAM-v3",
            api_key="",
            device="cuda",
            revision="e2e_rnnt",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    # Transformers publishes weights as microsoft/VibeVoice-ASR-HF; local CLI repos point at microsoft/VibeVoice-ASR.
    if BACKEND == "vibevoice_hf":
        return STTConfig(
            provider="vibevoice_hf",
            model="microsoft/VibeVoice-ASR-HF",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    msg = f"Unknown BACKEND={BACKEND!r}"
    raise ValueError(msg)


def build_service(cfg: STTConfig) -> SpeechRecognitionProtocol:  # noqa: PLR0911
    p = cfg.provider.lower().strip()
    if p in {"whisper_hf", "openai_whisper_hf"}:
        return WhisperHFSTTService(cfg)
    if p in {"russian_whisper_hf", "russian_whisper"}:
        return RussianWhisperHFSTTService(cfg)
    if p in {"granite_speech_hf", "granite_speech"}:
        return GraniteSpeechSTTService(cfg)
    if p in {"gigaam_hf", "gigaam"}:
        return GigaAMSTTService(cfg)
    if p in {"vibevoice_hf", "vibevoice"}:
        return VibeVoiceHFSTTService(cfg)
    if p == "openrouter_audio":
        return OpenRouterAudioService(cfg)
    if p in {"openrouter_audio_stt", "openrouter_stt"}:
        return OpenRouterAudioSTTService(cfg)
    msg = f"Unknown provider={cfg.provider!r}"
    raise ValueError(msg)


async def _main() -> None:
    cfg = build_stt_config()
    svc = build_service(cfg)

    for label, path in ("1-cold", AUDIO_1), ("2-warm", AUDIO_2):
        if not path.exists():
            print(f"[{label}] missing file: {path}", file=sys.stderr)  # noqa: T201
            sys.exit(1)
        t0 = time.perf_counter()
        tr = await svc.transcribe_audio(str(path.resolve()), LANG)
        dt = time.perf_counter() - t0
        print(f"[{label}] {dt:.2f}s  text={tr.text!r}")  # noqa: T201


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
