from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from lobanov.adapters.services.gigaam_stt_service import GigaAMSTTService
from lobanov.adapters.services.openrouter_audio_service import OpenRouterAudioService
from lobanov.adapters.services.openrouter_audio_stt_service import OpenRouterAudioSTTService
from lobanov.adapters.services.transformers_stt_service import TransformersSTTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol

load_dotenv()
# --- "transformers" | "openrouter_audio_stt" | "openrouter_audio" | "gigaam"
BACKEND = "gigaam"

AUDIO_1 = Path(r"C:\Users\dragonpuffle\Documents\диплом\audio\Сценарий 0 цефалгия.mp3")
AUDIO_2 = Path(r"C:\Users\dragonpuffle\Documents\диплом\audio\Сценарий 1 орви.mp3")

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

    if BACKEND == "openrouter_audio_stt":
        # openai/whisper-large-v3-turbo - 200
        # openai/gpt-4o-mini-transcribe - 200
        # openai/whisper-large-v3 - 200
        # openai/whisper-1 - 200
        # openai/gpt-4o-transcribe - 200

        return STTConfig(
            provider="openrouter_audio_stt",
            # id STT-модели в каталоге OpenRouter; при необходимости замени
            model="openai/whisper-large-v3-turbo",
            api_key=os.environ["OPENROUTER_API_KEY"],
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    if BACKEND == "openrouter_audio":
        # openai/gpt-audio-mini - 200
        # openai/gpt-4o-audio-preview - 200
        # openai/gpt-audio - 200
        return STTConfig(
            provider="openrouter_audio",
            # id audio-chat модели в каталоге OpenRouter; при необходимости замени
            model="openai/gpt-audio-mini",
            api_key=os.environ["OPENROUTER_API_KEY"],
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    if BACKEND == "transformers":
        # openai/whisper-large-v3-turbo - ок
        # openai/whisper-large-v3 - ок но долго
        # https://huggingface.co/dvislobokov/whisper-large-v3-turbo-russian - попробовать
        # https://huggingface.co/microsoft/VibeVoice-ASR - попробовать
        # https://huggingface.co/ai-sage/GigaAM-v3 - разобраться
        # https://huggingface.co/microsoft/Phi-4-multimodal-instruct - для этого возможно нужен будет новый адаптер
        # https://huggingface.co/t-tech/T-one - для этого возможно нужен будет новый адаптер
        return STTConfig(
            provider="transformers",
            model="openai/whisper-large-v3-turbo",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir="models/stt",
            **common,
        )

    if BACKEND == "gigaam":
        return STTConfig(
            provider="gigaam",
            model="ai-sage/GigaAM-v3",
            api_key="",
            device="cuda",
            # ssl | ctc | rnnt | e2e_ctc | e2e_rnnt — см. https://huggingface.co/ai-sage/GigaAM-v3
            revision="e2e_rnnt",
            compute_type="float16",
            model_cache_dir="models/stt",
            **common,
        )

    msg = f"Unknown BACKEND={BACKEND!r}"
    raise ValueError(msg)


def build_service(cfg: STTConfig) -> SpeechRecognitionProtocol:
    p = cfg.provider.lower().strip()
    if p == "gigaam":
        return GigaAMSTTService(cfg)
    if p == "openrouter_audio":
        return OpenRouterAudioService(cfg)
    if p == "openrouter_audio_stt":
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
