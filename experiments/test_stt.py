from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from lobanov.adapters.services.gigaam_stt_service import GigaAMSTTService
from lobanov.adapters.services.granite_speech_stt_service import GraniteSpeechSTTService
from lobanov.adapters.services.openrouter_audio_service import OpenRouterAudioService
from lobanov.adapters.services.openrouter_audio_stt_service import OpenRouterAudioSTTService
from lobanov.adapters.services.russian_whisper_hf_stt_service import RussianWhisperHFSTTService
from lobanov.adapters.services.transformers_stt_service import TransformersSTTService
from lobanov.adapters.services.vibevoice_asr_stt_service import VibeVoiceASRSTTService
from lobanov.adapters.services.whisper_hf_stt_service import WhisperHFSTTService
from lobanov.adapters.services.whisper_hf_v2_stt_service import WhisperHFV2STTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol

load_dotenv()
# backends: openrouter_* | transformers | gigaam | whisper_large_v3 | whisper_large_v3_turbo
# russian_whisper_turbo | whisper_large_v3_turbo_v2 | whisper_large_v3_v2 | granite_speech
# gigaam_e2e_rnnt | vibevoice_asr_hf
BACKEND = "whisper_large_v3_turbo_v2"

AUDIO_1 = Path(r"C:\Users\dragonpuffle\Documents\диплом\audio\Сценарий 0 цефалгия.mp3")
AUDIO_2 = Path(r"C:\Users\dragonpuffle\Documents\диплом\audio\Сценарий 1 орви.mp3")

LANG = "ru"


def build_stt_config() -> STTConfig:  # noqa: PLR0911, C901
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

    if BACKEND == "transformers":
        return STTConfig(
            provider="transformers",
            model="ibm-granite/granite-speech-4.1-2b",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "whisper_large_v3":
        return STTConfig(
            provider="whisper_hf",
            model="openai/whisper-large-v3",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "whisper_large_v3_turbo":
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

    if BACKEND == "whisper_large_v3_turbo_v2":
        return STTConfig(
            provider="whisper_hf_v2",
            model="openai/whisper-large-v3-turbo",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "whisper_large_v3_v2":
        return STTConfig(
            provider="whisper_hf_v2",
            model="openai/whisper-large-v3",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "russian_whisper_turbo":
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

    if BACKEND == "granite_speech":
        return STTConfig(
            provider="granite_speech",
            model="ibm-granite/granite-speech-4.1-2b",
            api_key="",
            device="cuda",
            revision="",
            compute_type="bfloat16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "gigaam_e2e_rnnt":
        return STTConfig(
            provider="gigaam",
            model="ai-sage/GigaAM-v3",
            api_key="",
            device="cuda",
            revision="e2e_rnnt",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "gigaam":
        return STTConfig(
            provider="gigaam",
            model="ai-sage/GigaAM-v3",
            api_key="",
            device="cuda",
            revision="e2e_rnnt",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    if BACKEND == "vibevoice_asr_hf":
        return STTConfig(
            provider="vibevoice_asr_hf",
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
    if p == "gigaam":
        return GigaAMSTTService(cfg)
    if p in {"whisper_hf_v2", "whisper_hf_v2_simple"}:
        return WhisperHFV2STTService(cfg)
    if p in {"whisper_hf", "openai_whisper_hf"}:
        return WhisperHFSTTService(cfg)
    if p in {"russian_whisper_hf", "whisper_ru_hf"}:
        return RussianWhisperHFSTTService(cfg)
    if p in {"granite_speech", "granite_speech_hf"}:
        return GraniteSpeechSTTService(cfg)
    if p in {"vibevoice_asr", "vibevoice_asr_hf"}:
        return VibeVoiceASRSTTService(cfg)
    if p == "openrouter_audio":
        return OpenRouterAudioService(cfg)
    if p in {"openrouter_audio_stt", "openrouter_stt"}:
        return OpenRouterAudioSTTService(cfg)
    if p == "transformers":
        return TransformersSTTService(cfg)
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
