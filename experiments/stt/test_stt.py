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

from lobanov.adapters.services.stt.openrouter_audio_service import OpenRouterAudioService
from lobanov.adapters.services.stt.openrouter_audio_stt_service import OpenRouterAudioSTTService
from lobanov.adapters.services.stt.whisper_hf_stt_service import WhisperHFSTTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol

load_dotenv()
# Supported: whisper_hf, openrouter_audio, openrouter_audio_stt
BACKEND = "whisper_hf"

AUDIO_1 = Path(r"experiments/audio/диалог-1-реал.mp3")
AUDIO_2 = Path(r"experiments/audio/диалог-15-эмиль.mp3")

LANG = "ru"


def build_stt_config() -> STTConfig:
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

    msg = f"Unknown BACKEND={BACKEND!r}"
    raise ValueError(msg)


def build_service(cfg: STTConfig) -> SpeechRecognitionProtocol:
    p = cfg.provider.lower().strip()
    if p in {"whisper_hf", "openai_whisper_hf"}:
        return WhisperHFSTTService(cfg)
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
