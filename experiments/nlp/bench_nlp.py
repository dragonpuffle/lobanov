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

import torch
from bert_score import BERTScorer
from dotenv import load_dotenv
from transformers import AutoModel, AutoTokenizer

from lobanov.adapters.services.nlp.llm_clinical_extraction_service import (
    ClinicalExtractionError,
    LLMClinicalExtractionService,
)
from lobanov.adapters.services.nlp.qwen3_hf_clinical_extraction_service import Qwen3HFClinicalExtractionService
from lobanov.domain.entities.template_field import TemplateField
from lobanov.infra.configs import NLPConfig
from lobanov.protocols import ClinicalExtractionProtocol
from lobanov.utils.logging import get_logger, setup_logging

load_dotenv()

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config — edit PROVIDER / MODEL / TRANSCRIPT_SOURCE to switch run target.
# Only ONE provider + ONE model is active per execution.
# ---------------------------------------------------------------------------

PROVIDER: Final[str] = "qwen3_hf"  # "openrouter" | "qwen3_hf"
MODEL: Final[str] = "Qwen/Qwen3-0.6B"  # one entry from PROVIDER_MODEL_CATALOGUE

# "expected"   — use the ideal transcript from dialog_transcripts.json
# "stt_result" — use the transcription field from an existing bench_*.json file
TRANSCRIPT_SOURCE: Final[str] = "stt_result"

# Required only when TRANSCRIPT_SOURCE == "stt_result".
# Relative paths are resolved from repo root; set to None to leave unused.
STT_RESULT_FILE: Final[Path | None] = Path(
    "experiments/results/stt/bench_whisper_hf_openai_whisper-large-v3-turbo_20260506_121806.json"
)
# Для stt_result задайте путь к JSON STT-бенча, например Path("experiments/results/stt/bench_….json").

MAX_ERRORS: Final[int] = 3

# Reference catalogue — all available configurations.
PROVIDER_MODEL_CATALOGUE: Final[dict[str, list[str]]] = {
    "qwen3_hf": [
        "Qwen/Qwen3-0.6B",
    ],
    "openrouter": [
        "deepseek/deepseek-v4-flash",
        "openai/gpt-4o-mini",
        "openai/gpt-oss-120b",  # too long
        "microsoft/phi-4",
    ],
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


TRANSCRIPTS_JSON: Final[Path] = repo_root() / "experiments" / "dialog_transcripts.json"
GT_FACTS_JSON: Final[Path] = repo_root() / "experiments" / "dialog_clinical_facts_01_30.json"
RESULTS_DIR: Final[Path] = repo_root() / "experiments" / "results" / "nlp"

_HF_DEVICE_DEFAULT: Final[str] = "cuda"
_HF_COMPUTE_TYPE: Final[str] = "float16"
_HF_NLP_CACHE: Final[str] = "models/nlp"

# ---------------------------------------------------------------------------
# Template fields — 11 fields, names match GT keys in dialog_clinical_facts_01_30.json
# ---------------------------------------------------------------------------

_TEMPLATE_ID = uuid4()
_NOW = datetime.now(UTC)

BENCHMARK_FIELDS: list[TemplateField] = [
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="patient_name",
        label="ФИО пациента",
        is_required=True,
        options=None,
        order=1,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="birth_date",
        label="Дата рождения",
        is_required=True,
        options=None,
        order=2,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="gender",
        label="Пол",
        is_required=True,
        options={"options": ["Мужской", "Женский"]},
        order=3,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="visit_date",
        label="Дата визита",
        is_required=False,
        options=None,
        order=4,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="chief_complaint",
        label="Жалобы",
        is_required=True,
        options=None,
        order=5,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="medical_history",
        label="Анамнез",
        is_required=False,
        options=None,
        order=6,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="allergies",
        label="Аллергии",
        is_required=False,
        options=None,
        order=7,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="examination",
        label="Осмотр",
        is_required=False,
        options=None,
        order=8,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="diagnosis",
        label="Диагноз",
        is_required=True,
        options=None,
        order=9,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="treatment_plan",
        label="План лечения",
        is_required=False,
        options=None,
        order=10,
        created_at=_NOW,
        updated_at=_NOW,
    ),
    TemplateField(
        id=uuid4(),
        template_id=_TEMPLATE_ID,
        name="doctor_name",
        label="ФИО врача",
        is_required=False,
        options=None,
        order=11,
        created_at=_NOW,
        updated_at=_NOW,
    ),
]

# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------


def build_nlp_config(provider: str, model: str) -> NLPConfig:
    p = provider.lower().strip()
    if p == "openrouter":
        return NLPConfig(
            use_mock=False,
            provider="openrouter",
            model=model,
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            max_tokens=4000,
            temperature=0.0,
            use_structured_output=False,
            use_response_healing=False,
        )
    if p in {"qwen3_hf", "qwen3", "qwen"}:
        return NLPConfig(
            use_mock=False,
            provider="qwen3_hf",
            model=model,
            api_key="",
            max_tokens=4096,
            temperature=0.0,
            use_structured_output=False,
            use_response_healing=False,
            device=_HF_DEVICE_DEFAULT,
            compute_type=_HF_COMPUTE_TYPE,
            revision="",
            model_cache_dir=_HF_NLP_CACHE,
            trust_remote_code=True,
        )
    msg = f"Unsupported provider: {provider!r}"
    raise ValueError(msg)


def build_service(cfg: NLPConfig) -> ClinicalExtractionProtocol:
    p = cfg.provider.lower().strip()
    if p == "openrouter":
        return LLMClinicalExtractionService(cfg)
    if p in {"qwen3_hf", "qwen3", "qwen3_06b"}:
        return Qwen3HFClinicalExtractionService(cfg)
    msg = f"Unknown provider={cfg.provider!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def load_dialogs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        msg = f"{path} must be a JSON array"
        raise TypeError(msg)
    return data


def load_gt_facts(path: Path) -> dict[str, dict[str, Any]]:
    """Return {dialog_id: clinical_facts_dict}; null values are preserved as-is."""
    records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return {str(r["dialog_id"]): dict(r.get("clinical_facts") or {}) for r in records}


def load_stt_results(path: Path) -> dict[str, dict[str, Any]]:
    """Return {dialog_id: record} from an existing bench_*.json results file."""
    records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return {str(r["dialog_id"]): r for r in records if "dialog_id" in r}


def _resolve_transcript(
    dialog_id: str,
    *,
    source: str,
    dialogs_index: dict[str, dict[str, Any]],
    stt_index: dict[str, dict[str, Any]] | None,
) -> tuple[str, str]:
    """Return (transcript_text, source_field_name) or raise ValueError on failure."""
    if source == "expected":
        rec = dialogs_index.get(dialog_id)
        if rec is None:
            msg = f"dialog_id={dialog_id!r} not found in dialog_transcripts.json"
            raise ValueError(msg)
        text = str(rec.get("expected_transcript") or "").strip()
        if not text:
            msg = f"empty expected_transcript for dialog_id={dialog_id!r}"
            raise ValueError(msg)
        return text, "expected_transcript"

    if source == "stt_result":
        if stt_index is None:
            msg = "stt_index is None but TRANSCRIPT_SOURCE=='stt_result'"
            raise ValueError(msg)
        rec = stt_index.get(dialog_id)
        if rec is None:
            msg = f"dialog_id={dialog_id!r} not found in STT result file"
            raise ValueError(msg)
        # Auto-detect the text field: current bench files all use "transcription",
        # but fall back to "text" or "expected_transcript" for robustness.
        for field in ("transcription", "text", "expected_transcript"):
            val = rec.get(field)
            if val and isinstance(val, str) and val.strip():
                return val.strip(), field
        msg = f"no non-empty transcript field found for dialog_id={dialog_id!r} in STT file"
        raise ValueError(msg)

    msg = f"Unknown TRANSCRIPT_SOURCE={source!r}"
    raise ValueError(msg)


_WARMUP_TRANSCRIPT_FALLBACK: Final[str] = (
    "Здравствуйте. ФИО пациента: Иванов Иван Иванович, 01.01.1990. Пол мужской. "
    "Жалобы: насморк, слабость. Аллергий не отмечает. До свидания."
)


async def warmup_nlp_run(
    svc: ClinicalExtractionProtocol,
    first_dialog: dict[str, Any] | None,
    *,
    dialogs_index: dict[str, dict[str, Any]],
    stt_index: dict[str, dict[str, Any]] | None,
) -> None:
    """Один проход извлечения без записи в результат: подгрузка весов модели и компиляций, не в бенч-таймингах."""
    transcript: str
    source_field: str
    did_repr: str

    if first_dialog is None:
        did_repr = "(нет)"
        transcript = _WARMUP_TRANSCRIPT_FALLBACK
        source_field = "warmup_stub_empty_catalog"
    else:
        did = str(first_dialog.get("dialog_id", ""))
        did_repr = did
        try:
            transcript, source_field = _resolve_transcript(
                did,
                source=TRANSCRIPT_SOURCE,
                dialogs_index=dialogs_index,
                stt_index=stt_index,
            )
        except ValueError as e:
            logger.warning(
                "Разогрев NLP: нет транскрипта для первого диалога ({}): {}. Заглушка.",
                did,
                e,
            )
            transcript = _WARMUP_TRANSCRIPT_FALLBACK
            source_field = "warmup_stub"

    logger.info(
        "Разогрев NLP: одно извлечение без записи в результаты, dialog_id={}, транскрипт из {}",
        did_repr,
        source_field,
    )
    try:
        await svc.extract_clinical_facts(transcript, BENCHMARK_FIELDS)
    except Exception:
        logger.exception("Разогрев NLP: ошибка извлечения")
        raise
    logger.info("Разогрев NLP завершён.")


# (mirrored from experiments/stt/bench_stt.py; shared cache directory)
# ---------------------------------------------------------------------------

_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_EMBED_MODEL: torch.nn.Module | None = None
_EMBED_TOKENIZER: Any = None
_EMBED_DEVICE: torch.device | None = None
_BERT_SCORER: BERTScorer | None = None

_RU_STOPWORDS: Final[frozenset[str]] = frozenset({
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
})


def _metrics_hf_cache_root() -> Path:
    p = repo_root() / "models" / "bench_metrics_hf"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _configure_hf_hub_for_metrics_cache() -> None:
    root = _metrics_hf_cache_root()
    hub = root / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_CACHE"] = str(hub.resolve())


def _mean_pool(last_hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = torch.sum(last_hidden * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _get_embedder() -> tuple[torch.nn.Module, Any, torch.device]:
    global _EMBED_MODEL, _EMBED_TOKENIZER, _EMBED_DEVICE  # noqa: PLW0603
    if _EMBED_MODEL is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cache_dir = str(_metrics_hf_cache_root())
        logger.info("Загрузка embedding-модели {} на {} …", _EMBED_MODEL_NAME, device)
        _EMBED_TOKENIZER = AutoTokenizer.from_pretrained(_EMBED_MODEL_NAME, cache_dir=cache_dir)
        _EMBED_MODEL = AutoModel.from_pretrained(_EMBED_MODEL_NAME, cache_dir=cache_dir)
        _EMBED_MODEL.to(device)
        _EMBED_MODEL.eval()
        _EMBED_DEVICE = device
    if _EMBED_TOKENIZER is None or _EMBED_DEVICE is None or _EMBED_MODEL is None:
        msg = "embedding model failed to initialize"
        raise RuntimeError(msg)
    return _EMBED_MODEL, _EMBED_TOKENIZER, _EMBED_DEVICE


def _get_bert_scorer() -> BERTScorer:
    if _BERT_SCORER is None:
        msg = "Call preload_metric_models() before computing metrics"
        raise RuntimeError(msg)
    return _BERT_SCORER


def preload_metric_models() -> None:
    """Load BERTScore (ru) and MiniLM once into memory; weights cached under models/bench_metrics_hf."""
    global _BERT_SCORER  # noqa: PLW0603
    if _BERT_SCORER is not None and _EMBED_MODEL is not None:
        logger.info("Модели метрик уже загружены, предзагрузка пропущена")
        return
    _configure_hf_hub_for_metrics_cache()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Предзагрузка BERTScore (ru), device={} …", device)
    _BERT_SCORER = BERTScorer(lang="ru", batch_size=8, device=device, rescale_with_baseline=False)
    _ = _BERT_SCORER.score(["прогрев"], ["прогрев"])
    logger.info("Предзагрузка embedding MiniLM …")
    _get_embedder()
    cache_root = _metrics_hf_cache_root().resolve()
    logger.info("Модели метрик готовы; кэш: {}", cache_root)


# ---------------------------------------------------------------------------
# Text metric primitives
# ---------------------------------------------------------------------------


def _alnum_words(text: str) -> list[str]:
    return re.findall(r"[0-9a-zа-яё]+", text.lower(), flags=re.IGNORECASE)


def _embedding_cosine(a: str, b: str) -> float:
    model, tokenizer, device = _get_embedder()
    with torch.no_grad():
        batch = tokenizer(
            [a, b],
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


def _bert_score_f1(hypothesis: str, reference: str) -> float:
    _, _, f1_tensor = _get_bert_scorer().score([hypothesis], [reference])
    return float(f1_tensor[0].item())


def _token_f1(hypothesis: str, reference: str) -> float:
    """Set-based F1 over content tokens (stopwords excluded)."""
    ref_tokens = {w for w in _alnum_words(reference) if w not in _RU_STOPWORDS and len(w) > 1}
    hyp_tokens = {w for w in _alnum_words(hypothesis) if w not in _RU_STOPWORDS and len(w) > 1}
    if not ref_tokens and not hyp_tokens:
        return 1.0
    if not ref_tokens or not hyp_tokens:
        return 0.0
    tp = len(ref_tokens & hyp_tokens)
    precision = tp / len(hyp_tokens)
    recall = tp / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _rouge_l_f1(hypothesis: str, reference: str) -> float:
    """ROUGE-L F1 via LCS over token sequences; no external dependency."""
    ref_words = _alnum_words(reference)
    hyp_words = _alnum_words(hypothesis)
    if not ref_words and not hyp_words:
        return 1.0
    if not ref_words or not hyp_words:
        return 0.0
    m, n = len(ref_words), len(hyp_words)
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    lcs = prev[n]
    precision = lcs / n
    recall = lcs / m
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Normalization helpers for exact-match on structured fields
# ---------------------------------------------------------------------------

_DATE_RE_DMY = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})")
_DATE_RE_YMD = re.compile(r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})")


def _normalize_date(text: str) -> str | None:
    """Return DD.MM.YYYY string, or None if no parseable date found."""
    t = text.strip()
    m = _DATE_RE_YMD.search(t)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    m = _DATE_RE_DMY.search(t)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{d}.{mo}.{y}"
    return None


_GENDER_MAP: Final[dict[str, str]] = {
    "мужской": "мужской",
    "мужчина": "мужской",
    "муж": "мужской",
    "мужского": "мужской",
    "м": "мужской",
    "male": "мужской",
    "женский": "женский",
    "женщина": "женский",
    "жен": "женский",
    "женского": "женский",
    "ж": "женский",
    "female": "женский",
}


def _normalize_gender(text: str) -> str | None:
    return _GENDER_MAP.get(text.lower().strip())


def _normalize_name(text: str) -> str:
    return " ".join(text.casefold().split())


# ---------------------------------------------------------------------------
# Per-field metrics
# ---------------------------------------------------------------------------

_FREE_TEXT_FIELDS: Final[frozenset[str]] = frozenset({
    "chief_complaint",
    "medical_history",
    "allergies",
    "examination",
    "diagnosis",
    "treatment_plan",
})
_DATE_FIELDS: Final[frozenset[str]] = frozenset({"birth_date", "visit_date"})
_NAME_FIELDS: Final[frozenset[str]] = frozenset({"patient_name", "doctor_name"})


def _is_filled(v: Any) -> bool:
    return bool(v is not None and str(v).strip())


def compute_per_field_metrics(
    field_name: str,
    gt_value: Any,
    pred_value: str,
) -> dict[str, Any]:
    gt_filled = _is_filled(gt_value)
    pred_filled = _is_filled(pred_value)
    gt_str = str(gt_value).strip() if gt_filled else ""
    pred_str = pred_value.strip() if pred_filled else ""

    result: dict[str, Any] = {
        "gt_value": gt_str if gt_filled else None,
        "pred_value": pred_str if pred_filled else None,
        "gt_filled": gt_filled,
        "pred_filled": pred_filled,
        "exact_match": None,
        "token_f1": None,
        "bert_score_f1": None,
        "embedding_cosine": None,
        "rouge_l_f1": None,
    }

    # Exact match — type-specific normalization
    if field_name in _DATE_FIELDS:
        gt_norm = _normalize_date(gt_str) if gt_filled else None
        pred_norm = _normalize_date(pred_str) if pred_filled else None
        if gt_norm is not None and pred_norm is not None:
            result["exact_match"] = gt_norm == pred_norm
        else:
            result["exact_match"] = gt_str.strip() == pred_str.strip()
    elif field_name == "gender":
        gt_norm = _normalize_gender(gt_str)
        pred_norm = _normalize_gender(pred_str)
        if gt_norm and pred_norm:
            result["exact_match"] = gt_norm == pred_norm
        else:
            result["exact_match"] = gt_str.lower() == pred_str.lower()
    elif field_name in _NAME_FIELDS:
        result["exact_match"] = _normalize_name(gt_str) == _normalize_name(pred_str)
    else:
        result["exact_match"] = gt_str.casefold() == pred_str.casefold()

    # Text metrics — only for free-text fields when both sides are non-empty
    if field_name in _FREE_TEXT_FIELDS and gt_filled and pred_filled:
        result["token_f1"] = _token_f1(pred_str, gt_str)
        result["rouge_l_f1"] = _rouge_l_f1(pred_str, gt_str)
        result["bert_score_f1"] = _bert_score_f1(pred_str, gt_str)
        result["embedding_cosine"] = _embedding_cosine(pred_str, gt_str)

    return result


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------


def compute_aggregate_metrics(per_field: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    for m in per_field.values():
        gf, pf = m["gt_filled"], m["pred_filled"]
        if gf and pf:
            tp += 1
        elif not gf and pf:
            fp += 1
        elif gf and not pf:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(per_field) if per_field else 0.0

    em_values = [m["exact_match"] for m in per_field.values() if m["gt_filled"] and m["exact_match"] is not None]
    exact_match_accuracy = (sum(em_values) / len(em_values)) if em_values else None

    def _mean_metric(key: str) -> float | None:
        vals = [m[key] for m in per_field.values() if m.get(key) is not None]
        return (sum(vals) / len(vals)) if vals else None

    return {
        "field_filling": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "accuracy": round(accuracy, 6),
        },
        "exact_match_accuracy": round(exact_match_accuracy, 6) if exact_match_accuracy is not None else None,
        "mean_token_f1": _mean_metric("token_f1"),
        "mean_bert_score_f1": _mean_metric("bert_score_f1"),
        "mean_embedding_cosine": _mean_metric("embedding_cosine"),
        "mean_rouge_l_f1": _mean_metric("rouge_l_f1"),
    }


# ---------------------------------------------------------------------------
# Result I/O helpers
# ---------------------------------------------------------------------------


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


def _output_path_for_run(provider: str, model: str, source: str) -> Path:
    slug_model = re.sub(r"[^a-zA-Z0-9_\-]", "_", model)
    slug_provider = re.sub(r"[^a-zA-Z0-9_\-]", "_", provider)
    slug_source = re.sub(r"[^a-zA-Z0-9_\-]", "_", source)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / f"bench_nlp_{slug_provider}_{slug_model}_{slug_source}_{ts}.json"


# ---------------------------------------------------------------------------
# Benchmark error type
# ---------------------------------------------------------------------------


class BenchmarkAbortedError(Exception):
    """Raised when cumulative dialog failures reach MAX_ERRORS."""


# ---------------------------------------------------------------------------
# Single-dialog runner
# ---------------------------------------------------------------------------


async def run_single(  # noqa: PLR0913, PLR0915
    dialog: dict[str, Any],
    svc: ClinicalExtractionProtocol,
    provider: str,
    model: str,
    experiment_id: UUID,
    results_path: Path,
    *,
    gt_index: dict[str, dict[str, Any]],
    dialogs_index: dict[str, dict[str, Any]],
    stt_index: dict[str, dict[str, Any]] | None,
    step_index: int,
    step_total: int,
) -> tuple[bool, str | None]:
    dialog_id = str(dialog.get("dialog_id", ""))
    logger.info("Диалог {}/{} — старт: {}", step_index, step_total, dialog_id)

    base_record: dict[str, Any] = {
        "experiment_id": str(experiment_id),
        "dialog_id": dialog_id,
        "provider": provider,
        "model": model,
        "transcript_source": TRANSCRIPT_SOURCE,
        "stt_result_file": str(STT_RESULT_FILE) if STT_RESULT_FILE else None,
        "transcript_field": None,
        "transcript": None,
        "elapsed_seconds": None,
        "extracted_facts": None,
        "metrics": None,
        "error": None,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    # 1. Resolve transcript text
    try:
        transcript, transcript_field = _resolve_transcript(
            dialog_id,
            source=TRANSCRIPT_SOURCE,
            dialogs_index=dialogs_index,
            stt_index=stt_index,
        )
        base_record["transcript_field"] = transcript_field
        base_record["transcript"] = transcript
    except ValueError as e:
        err = str(e)
        logger.warning("Диалог {}/{} [{}]: нет транскрипта — {}", step_index, step_total, dialog_id, err)
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    # 2. Extract clinical facts
    try:
        t0 = time.perf_counter()
        facts = await svc.extract_clinical_facts(transcript, BENCHMARK_FIELDS)
        elapsed = time.perf_counter() - t0
    except ClinicalExtractionError as e:
        err = f"ClinicalExtractionError: {e}"
        logger.warning("Диалог {}/{} [{}]: ошибка извлечения — {}", step_index, step_total, dialog_id, err)
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        logger.exception("Диалог {}/{} [{}]: неожиданная ошибка извлечения", step_index, step_total, dialog_id)
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    base_record["elapsed_seconds"] = round(elapsed, 4)

    # 3. Build extracted_facts dict keyed by field name
    field_id_to_name = {f.id: f.name for f in BENCHMARK_FIELDS}
    extracted: dict[str, dict[str, Any]] = {}
    for fact in facts:
        fname = field_id_to_name.get(fact.template_field_id)
        if fname:
            extracted[fname] = {
                "value": fact.value,
                "confidence": fact.confidence,
                "source_text": fact.source_text,
            }
    base_record["extracted_facts"] = extracted

    # 4. Compute metrics vs GT
    gt_facts = gt_index.get(dialog_id, {})
    try:
        per_field: dict[str, dict[str, Any]] = {}
        for field in BENCHMARK_FIELDS:
            fname = field.name
            gt_val = gt_facts.get(fname)  # may be None (absent or explicitly null in GT)
            pred_val = (extracted.get(fname) or {}).get("value") or ""
            per_field[fname] = compute_per_field_metrics(fname, gt_val, pred_val)
        aggregate = compute_aggregate_metrics(per_field)
        base_record["metrics"] = {"per_field": per_field, "aggregate": aggregate}
    except Exception as e:
        err = f"metrics failed: {type(e).__name__}: {e}"
        logger.exception("Диалог {}/{} [{}]: ошибка подсчёта метрик (факты есть)", step_index, step_total, dialog_id)
        base_record["error"] = err
        append_result_record(results_path, base_record)
        return False, err

    # 5. Persist immediately
    append_result_record(results_path, base_record)
    filling_f1 = aggregate["field_filling"]["f1"]
    logger.info(
        "Диалог {}/{} [{}] готов: {:.2f}s  фактов={}  filling_f1={:.3f}",
        step_index,
        step_total,
        dialog_id,
        elapsed,
        len(facts),
        filling_f1,
    )
    return True, None


# ---------------------------------------------------------------------------
# All-dialogs runner
# ---------------------------------------------------------------------------


async def run_all(  # noqa: PLR0913
    dialogs: list[dict[str, Any]],
    svc: ClinicalExtractionProtocol,
    provider: str,
    model: str,
    experiment_id: UUID,
    results_path: Path,
    *,
    gt_index: dict[str, dict[str, Any]],
    dialogs_index: dict[str, dict[str, Any]],
    stt_index: dict[str, dict[str, Any]] | None,
) -> tuple[int, int]:
    """Run benchmark over all dialogs; return (success_count, failure_count)."""
    ok_count = fail_count = total_errors = 0
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
            gt_index=gt_index,
            dialogs_index=dialogs_index,
            stt_index=stt_index,
            step_index=i + 1,
            step_total=n,
        )
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            total_errors += 1
            logger.warning(
                "Неудача {}/{} [{}]. Накоплено ошибок: {}/{} (лимит остановки)",
                i + 1,
                n,
                dialog.get("dialog_id", "?"),
                total_errors,
                MAX_ERRORS,
            )
            if err:
                logger.warning("Причина: {}", err)
            if total_errors >= MAX_ERRORS:
                msg = f"Stopped after {MAX_ERRORS} cumulative failed dialogs"
                logger.error("Остановка: накопилось {} ошибок. {}", MAX_ERRORS, msg)
                raise BenchmarkAbortedError(msg)

    logger.info("Основной цикл завершён: успехов={}, неудач={}", ok_count, fail_count)
    return ok_count, fail_count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _validate_nlp_run_config() -> Path | None:
    """Проверка констант; при ошибке вызывает sys.exit(1). Возвращает путь STT или None."""
    if PROVIDER not in PROVIDER_MODEL_CATALOGUE:
        logger.error("Неизвестный PROVIDER={}. Доступные: {}", PROVIDER, list(PROVIDER_MODEL_CATALOGUE))
        sys.exit(1)
    if MODEL not in PROVIDER_MODEL_CATALOGUE.get(PROVIDER, []):
        logger.warning("Модель {} не найдена в каталоге для провайдера {}. Продолжаем.", MODEL, PROVIDER)
    if TRANSCRIPT_SOURCE not in ("expected", "stt_result"):
        logger.error("Неверный TRANSCRIPT_SOURCE={}. Допустимые: 'expected', 'stt_result'", TRANSCRIPT_SOURCE)
        sys.exit(1)
    if TRANSCRIPT_SOURCE != "stt_result":
        return None
    if STT_RESULT_FILE is None:
        logger.error("STT_RESULT_FILE не задан при TRANSCRIPT_SOURCE='stt_result'")
        sys.exit(1)
    abs_stt = STT_RESULT_FILE if STT_RESULT_FILE.is_absolute() else (repo_root() / STT_RESULT_FILE).resolve()
    if not abs_stt.is_file():
        logger.error("STT_RESULT_FILE не найден: {}", abs_stt)
        sys.exit(1)
    return abs_stt


def _load_nlp_benchmark_data(
    abs_stt_path: Path | None,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]] | None,
]:
    if not TRANSCRIPTS_JSON.is_file():
        logger.error("Файл диалогов не найден: {}", TRANSCRIPTS_JSON)
        sys.exit(1)
    logger.info("Загрузка диалогов: {}", TRANSCRIPTS_JSON)
    dialogs = load_dialogs(TRANSCRIPTS_JSON)
    dialogs_index = {str(d["dialog_id"]): d for d in dialogs if "dialog_id" in d}
    logger.info("Загружено диалогов: {}", len(dialogs))

    if not GT_FACTS_JSON.is_file():
        logger.error("GT facts file не найден: {}", GT_FACTS_JSON)
        sys.exit(1)
    logger.info("Загрузка GT фактов: {}", GT_FACTS_JSON)
    gt_index = load_gt_facts(GT_FACTS_JSON)
    logger.info("Загружено GT записей: {}", len(gt_index))

    stt_index: dict[str, dict[str, Any]] | None = None
    if abs_stt_path is not None:
        logger.info("Загрузка STT результатов: {}", abs_stt_path)
        stt_index = load_stt_results(abs_stt_path)
        logger.info("Загружено STT записей: {}", len(stt_index))

    return dialogs, dialogs_index, gt_index, stt_index


def _build_nlp_svc_or_exit() -> ClinicalExtractionProtocol:
    logger.info("Инициализация NLP-сервиса (provider={}, model={}) …", PROVIDER, MODEL)
    cfg = build_nlp_config(PROVIDER, MODEL)
    if cfg.provider == "openrouter" and not cfg.api_key.strip():
        logger.error("OPENROUTER_API_KEY пуст или не задан")
        sys.exit(1)
    svc = build_service(cfg)
    logger.info("NLP-сервис готов")
    return svc


async def _main() -> None:
    logger.info("Старт bench_nlp: провайдер={}, модель={}, источник={}", PROVIDER, MODEL, TRANSCRIPT_SOURCE)
    abs_stt_path = _validate_nlp_run_config()

    exp_id = uuid4()
    results_path = _output_path_for_run(PROVIDER, MODEL, TRANSCRIPT_SOURCE)
    logger.info("experiment_id={}", exp_id)
    logger.info("Файл результатов: {}", results_path)

    dialogs, dialogs_index, gt_index, stt_index = _load_nlp_benchmark_data(abs_stt_path)
    svc = _build_nlp_svc_or_exit()
    if dialogs:
        await warmup_nlp_run(svc, dialogs[0], dialogs_index=dialogs_index, stt_index=stt_index)
    else:
        logger.warning("Разогрев NLP пропущен: нет диалогов в каталоге")
    preload_metric_models()

    try:
        ok_n, fail_n = await run_all(
            dialogs,
            svc,
            PROVIDER,
            MODEL,
            exp_id,
            results_path,
            gt_index=gt_index,
            dialogs_index=dialogs_index,
            stt_index=stt_index,
        )
    except BenchmarkAbortedError as e:
        logger.warning("Бенчмарк прерван: {}", e)
        sys.exit(2)

    logger.info("Бенчмарк завершён: успехов={}, неудач={}", ok_n, fail_n)


def main() -> None:
    setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
    asyncio.run(_main())


if __name__ == "__main__":
    main()
