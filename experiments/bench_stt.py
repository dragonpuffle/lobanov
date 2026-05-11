# ruff: noqa: E402, T201

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
from uuid import UUID, uuid4

from dotenv import load_dotenv

from lobanov.compat.transformers_asr_no_torchcodec import disable_torchcodec_probe_for_asr

disable_torchcodec_probe_for_asr()

import torch
from bert_score import BERTScorer
from jiwer import cer, wer
from transformers import AutoModel, AutoTokenizer

from lobanov.adapters.services.stt.openrouter_audio_service import OpenRouterAudioService
from lobanov.adapters.services.stt.openrouter_audio_stt_service import OpenRouterAudioSTTService
from lobanov.adapters.services.stt.whisper_hf_stt_service import WhisperHFSTTService
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger, setup_logging

load_dotenv()

logger = get_logger(__name__)

# ONE provider + ONE model per run
PROVIDER: Final[str] = "openrouter_audio"
MODEL: Final[str] = "openai/gpt-audio-mini"
LANG: Final[str] = "ru"

MAX_ERRORS: Final[int] = 3

# reference catalogue (not executed, just documented)
PROVIDER_MODEL_CATALOGUE: Final[dict[str, list[str]]] = {
    "whisper_hf": [
        "openai/whisper-medium",
        "openai/whisper-large-v3-turbo",
        "openai/whisper-large-v3",
        "openai/whisper-base",
    ],
    "openrouter_audio_stt": [
        "openai/gpt-4o-transcribe",
        "openai/whisper-1",
        "openai/whisper-large-v3",
        "openai/whisper-large-v3-turbo",
        "openai/gpt-4o-mini-transcribe",
    ],
    "openrouter_audio": [
        "openai/gpt-audio",
        "openai/gpt-audio-mini",
        "openai/gpt-4o-audio-preview",
    ],
}

# Minimal Russian stopwords for clinical_term_recall content-word extraction
_RU_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "и",
        "в",
        "во",
        "не",
        "что",
        "он",
        "на",
        "я",
        "с",
        "со",
        "как",
        "а",
        "то",
        "все",
        "она",
        "так",
        "его",
        "но",
        "да",
        "ты",
        "к",
        "у",
        "же",
        "вы",
        "за",
        "бы",
        "по",
        "только",
        "ее",
        "мне",
        "было",
        "вот",
        "от",
        "меня",
        "еще",
        "нет",
        "о",
        "из",
        "ему",
        "теперь",
        "когда",
        "даже",
        "ну",
        "вдруг",
        "ли",
        "если",
        "уже",
        "или",
        "быть",
        "был",
        "него",
        "до",
        "вас",
        "ни",
        "уж",
        "вам",
        "ведь",
        "там",
        "потом",
        "себя",
        "ничего",
        "ей",
        "может",
        "они",
        "тут",
        "где",
        "есть",
        "надо",
        "ней",
        "для",
        "мы",
        "тебя",
        "их",
        "чем",
        "была",
        "сам",
        "чтоб",
        "без",
        "будто",
        "чего",
        "раз",
        "тоже",
        "себе",
        "под",
        "будет",
        "ж",
        "тогда",
        "кто",
        "этот",
        "того",
        "потому",
        "этого",
        "какой",
        "совсем",
        "ним",
        "здесь",
        "этом",
        "один",
        "почти",
        "мой",
        "тем",
        "чтобы",
        "нее",
        "сейчас",
        "были",
        "куда",
        "зачем",
        "всех",
        "никогда",
        "можно",
        "при",
        "наконец",
        "два",
        "об",
        "другой",
        "хоть",
        "после",
        "над",
        "больше",
        "тот",
        "через",
        "эти",
        "нас",
        "про",
        "всего",
        "них",
        "какая",
        "много",
        "разве",
        "три",
        "эту",
        "моя",
        "впрочем",
        "хорошо",
        "свою",
        "этой",
        "перед",
        "иногда",
        "лучше",
        "чуть",
        "том",
        "нельзя",
        "такой",
        "им",
        "более",
        "всегда",
        "конечно",
        "всю",
        "между",
        "дак",
        "это",
        "здравствуйте",
        "спасибо",
        "пожалуйста",
        "свидания",
        "день",
        "добрый",
    },
)


def _jiwer_preprocess(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace (Cyrillic + Latin letters, digits)."""
    lowered = text.lower()
    cleaned = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    return " ".join(cleaned.split())


_EMBED_MODEL: torch.nn.Module | None = None
_EMBED_TOKENIZER: Any = None
_EMBED_DEVICE: torch.device | None = None

_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_BERT_SCORER: BERTScorer | None = None


def _mean_pool(last_hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = torch.sum(last_hidden * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _get_embedder() -> tuple[torch.nn.Module, Any, torch.device]:
    global _EMBED_MODEL, _EMBED_TOKENIZER, _EMBED_DEVICE  # noqa: PLW0603
    if _EMBED_MODEL is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cache_dir = str(metrics_hf_cache_root())
        logger.info(
            "Загрузка embedding-модели {} на {} (cache_dir={})",
            _EMBED_MODEL_NAME,
            device,
            cache_dir,
        )
        _EMBED_TOKENIZER = AutoTokenizer.from_pretrained(_EMBED_MODEL_NAME, cache_dir=cache_dir)
        _EMBED_MODEL = AutoModel.from_pretrained(_EMBED_MODEL_NAME, cache_dir=cache_dir)
        _EMBED_MODEL.to(device)
        _EMBED_MODEL.eval()
        _EMBED_DEVICE = device
    if _EMBED_TOKENIZER is None or _EMBED_DEVICE is None or _EMBED_MODEL is None:
        msg = "embedding model failed to initialize"
        raise RuntimeError(msg)
    return _EMBED_MODEL, _EMBED_TOKENIZER, _EMBED_DEVICE


def _alnum_words(text: str) -> list[str]:
    """Lowercase words containing letters or digits."""
    lowered = text.lower()
    # Keep Cyrillic + Latin letters and digits as word tokens
    return re.findall(r"[0-9a-zа-яё]+", lowered, flags=re.IGNORECASE)


def clinical_term_recall(reference: str, hypothesis: str) -> float:
    ref_words = set(_alnum_words(reference))
    hyp_words = set(_alnum_words(hypothesis))
    clinical = {w for w in ref_words if w not in _RU_STOPWORDS and len(w) > 1}
    if not clinical:
        return 1.0
    hits = sum(1 for w in clinical if w in hyp_words)
    return hits / len(clinical)


def embedding_cosine(reference: str, hypothesis: str) -> float:
    model, tokenizer, device = _get_embedder()
    with torch.no_grad():
        batch = tokenizer(
            [reference, hypothesis],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        batch = {k: v.to(device) for k, v in batch.items()}
        out = model(**batch)
        pooled = _mean_pool(out.last_hidden_state, batch["attention_mask"])
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return float((pooled[0] * pooled[1]).sum().item())


def _get_bert_scorer() -> BERTScorer:
    if _BERT_SCORER is None:
        msg = "Вызовите preload_metric_models() до подсчёта метрик"
        raise RuntimeError(msg)
    return _BERT_SCORER


def preload_metric_models() -> None:
    """Один раз загружает BERTScore и MiniLM; веса кладутся в ``models/bench_metrics_hf``."""
    global _BERT_SCORER  # noqa: PLW0603
    if _BERT_SCORER is not None and _EMBED_MODEL is not None:
        logger.info("Модели метрик уже загружены в память, предзагрузка пропущена")
        return

    root = configure_hf_hub_for_metrics_cache()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Предзагрузка BERTScore (ru), device={} …", device)
    _BERT_SCORER = BERTScorer(
        lang="ru",
        batch_size=8,
        device=device,
        rescale_with_baseline=False,
    )
    _ = _BERT_SCORER.score(["прогрев"], ["прогрев"])

    logger.info("Предзагрузка embedding MiniLM …")
    _get_embedder()

    logger.info("Модели для метрик готовы; кэш: {}", root.resolve())


def compute_metrics(reference: str, hypothesis: str) -> dict[str, float]:
    ref_j = _jiwer_preprocess(reference)
    hyp_j = _jiwer_preprocess(hypothesis)

    cer_val = cer(ref_j, hyp_j)
    wer_val = wer(ref_j, hyp_j)

    _, _, f1_tensor = _get_bert_scorer().score([hypothesis], [reference])
    bert_f1 = float(f1_tensor[0].item())

    emb_cos = embedding_cosine(reference, hypothesis)
    ctr = clinical_term_recall(reference, hypothesis)

    return {
        "cer": float(cer_val),
        "wer": float(wer_val),
        "bert_score_f1": bert_f1,
        "embedding_cosine": emb_cos,
        "clinical_term_recall": ctr,
    }


def build_stt_config(provider: str, model: str) -> STTConfig:
    common: dict[str, Any] = {
        "language": LANG,
        "model": model,
        "beam_size": 5,
        "vad_filter": True,
        "word_timestamps": True,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "condition_on_previous_text": True,
        "initial_prompt": "",
    }

    cache = "models/stt"
    p = provider.lower().strip()

    if p == "openrouter_audio_stt":
        return STTConfig(
            provider="openrouter_audio_stt",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    if p == "openrouter_audio":
        return STTConfig(
            provider="openrouter_audio",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            device="cpu",
            revision="",
            compute_type="float32",
            **common,
        )

    if p in {"whisper_hf", "openai_whisper_hf"}:
        return STTConfig(
            provider="whisper_hf",
            api_key="",
            device="cuda",
            revision="",
            compute_type="float16",
            model_cache_dir=cache,
            **common,
        )

    msg = f"Unsupported provider for benchmark: {provider!r}"
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


class BenchmarkAbortedError(Exception):
    """Too dialog failures in a row cumulative — benchmark stopped."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def metrics_hf_cache_root() -> Path:
    """Локальный кэш HF для метрик (BERT + MiniLM); переиспользуется между запусками."""
    p = repo_root() / "models" / "bench_metrics_hf"
    p.mkdir(parents=True, exist_ok=True)
    return p


def configure_hf_hub_for_metrics_cache() -> Path:
    """Перенаправить загрузки Hub для метрик в ``models/bench_metrics_hf/hub`` (после разогрева STT)."""
    root = metrics_hf_cache_root()
    hub = root / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_CACHE"] = str(hub.resolve())
    return root


def load_dialogs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        msg = "dialog_transcripts.json must be a JSON array"
        raise TypeError(msg)
    return data


def _ensure_results_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        msg = f"Results file {path} must contain a JSON array"
        raise TypeError(msg)
    return data


def append_result_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _ensure_results_list(path)
    records.append(record)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


async def warmup_run(svc: SpeechRecognitionProtocol, first_dialog: dict[str, Any]) -> None:
    did = str(first_dialog.get("dialog_id", ""))
    audio_rel = str(first_dialog.get("audio_path", ""))
    abs_path = (repo_root() / audio_rel).resolve()
    if not abs_path.is_file():
        logger.warning(
            "Разогрев: пропуск — нет файла {}, dialog_id={}",
            abs_path,
            did,
        )
        return
    logger.info(
        "Разогрев STT: одна транскрипция без записи в результаты, dialog_id={}, файл={}",
        did,
        abs_path.name,
    )
    try:
        await svc.transcribe_audio(str(abs_path), LANG)
    except Exception:
        logger.exception("Разогрев STT: ошибка транскрипции")
        raise
    logger.info("Разогрев STT завершён.")


async def run_single(  # noqa: PLR0913
    dialog: dict[str, Any],
    svc: SpeechRecognitionProtocol,
    provider: str,
    model: str,
    experiment_id: UUID,
    results_path: Path,
    *,
    step_index: int,
    step_total: int,
) -> tuple[bool, str | None]:
    dialog_id = str(dialog.get("dialog_id", ""))
    audio_rel = str(dialog.get("audio_path", ""))
    expected = str(dialog.get("expected_transcript", ""))
    abs_path = (repo_root() / audio_rel).resolve()

    logger.info(
        "Диалог {}/{} — старт: {} ({})",
        step_index,
        step_total,
        dialog_id,
        audio_rel or abs_path.name,
    )

    base_record: dict[str, Any] = {
        "experiment_id": str(experiment_id),
        "dialog_id": dialog_id,
        "provider": provider,
        "model": model,
        "audio_path": audio_rel,
        "elapsed_seconds": None,
        "transcription": None,
        "metrics": None,
        "error": None,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    if not abs_path.is_file():
        err = f"Audio file not found: {abs_path}"
        logger.error(
            "Диалог {}/{} [{}]: нет аудио '{}'",
            step_index,
            step_total,
            dialog_id,
            abs_path,
        )
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    try:
        t0 = time.perf_counter()
        transcript = await svc.transcribe_audio(str(abs_path), LANG)
        elapsed = time.perf_counter() - t0
        hyp = transcript.text.strip()
    except SpeechRecognitionError as e:
        err = str(e)
        logger.warning(
            "Диалог {}/{} [{}]: ошибка транскрипции (SpeechRecognition): {}",
            step_index,
            step_total,
            dialog_id,
            err,
        )
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        logger.exception(
            "Диалог {}/{} [{}]: неожиданная ошибка транскрипции",
            step_index,
            step_total,
            dialog_id,
        )
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    try:
        m = compute_metrics(expected, hyp)
    except Exception as e:
        err = f"metrics failed: {type(e).__name__}: {e}"
        logger.exception(
            "Диалог {}/{} [{}]: ошибка при подсчёте метрик (транскрипция есть)",
            step_index,
            step_total,
            dialog_id,
        )
        base_record["elapsed_seconds"] = round(elapsed, 4)
        base_record["transcription"] = hyp
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    base_record["elapsed_seconds"] = round(elapsed, 4)
    base_record["transcription"] = hyp
    base_record["metrics"] = m
    append_result_record(results_path, base_record)
    return True, None


async def run_all(  # noqa: PLR0913
    dialogs: list[dict[str, Any]],
    svc: SpeechRecognitionProtocol,
    provider: str,
    model: str,
    experiment_id: UUID,
    results_path: Path,
) -> tuple[int, int]:
    """Run benchmark; return (success_count, failure_count)."""
    ok_count = 0
    fail_count = 0
    total_errors = 0
    n = len(dialogs)
    logger.info("Основной цикл: {} диалогов", n)

    for i, dialog in enumerate(dialogs):
        ok, err = await run_single(
            dialog,
            svc,
            provider,
            model,
            experiment_id,
            results_path,
            step_index=i + 1,
            step_total=n,
        )
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            total_errors += 1
            logger.warning(
                "Основной цикл: неудача {}/{}, {}. Накоплено неудач: {}/{} (лимит остановки)",
                i + 1,
                n,
                dialog.get("dialog_id", "?"),
                total_errors,
                MAX_ERRORS,
            )
            if err:
                logger.warning("Причина: {}", err)
            if total_errors >= MAX_ERRORS:
                msg = f"Stopped after {MAX_ERRORS} failed dialogs (accumulated)"
                logger.error(
                    "Остановка: накопилось {} неудачных диалогов. {}",
                    MAX_ERRORS,
                    msg,
                )
                raise BenchmarkAbortedError(msg)

    logger.info("Основной цикл завершён: успехов={}, неудач={}", ok_count, fail_count)
    return ok_count, fail_count


def _output_path_for_run(provider: str, model: str) -> Path:
    slug_model = model.replace("/", "_").replace(" ", "_")
    slug_provider = provider.replace("/", "_").replace(" ", "_")
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return repo_root() / "experiments" / "results" / f"bench_{slug_provider}_{slug_model}_{ts}.json"


async def _main() -> None:
    logger.info("Старт bench_stt: провайдер={}, модель={}", PROVIDER, MODEL)

    if PROVIDER not in PROVIDER_MODEL_CATALOGUE:
        logger.error("Неизвестный провайдер: {!r}", PROVIDER)
        print(f"Unknown PROVIDER={PROVIDER!r}. Valid: {list(PROVIDER_MODEL_CATALOGUE)}", file=sys.stderr)
        sys.exit(1)

    exp_id = uuid4()
    results_path = _output_path_for_run(PROVIDER, MODEL)
    logger.info("experiment_id={}", exp_id)
    logger.info("Файл результатов: {}", results_path)
    print(f"Experiment ID: {exp_id}")
    print(f"Results file: {results_path}")

    dialogs_path = repo_root() / "experiments" / "dialog_transcripts.json"
    logger.info("Загрузка каталога диалогов: {}", dialogs_path)
    dialogs = load_dialogs(dialogs_path)
    logger.info("Загружено записей: {}", len(dialogs))

    logger.info("Инициализация STT…")
    cfg = build_stt_config(PROVIDER, MODEL)
    if cfg.provider.startswith("openrouter") and not cfg.api_key.strip():
        logger.error("OPENROUTER_API_KEY пуст или не задан")
        print("OPENROUTER_API_KEY is empty or missing.", file=sys.stderr)
        sys.exit(1)

    logger.info("Сервис STT: {}", cfg.provider)
    svc = build_service(cfg)

    if dialogs:
        await warmup_run(svc, dialogs[0])
    else:
        logger.warning("Разогрев STT пропущен: нет диалогов")

    preload_metric_models()

    try:
        ok_n, fail_n = await run_all(dialogs, svc, PROVIDER, MODEL, exp_id, results_path)
    except BenchmarkAbortedError as e:
        logger.warning("Бенчмарк прерван: {}", e)
        print(f"Benchmark aborted: {e}", file=sys.stderr)
        sys.exit(2)

    logger.info("Бенчмарк завершён: успехов={}, неудач={}", ok_n, fail_n)
    print(f"Done. Successes: {ok_n}, failures: {fail_n}")


def main() -> None:
    setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
    asyncio.run(_main())


if __name__ == "__main__":
    main()
