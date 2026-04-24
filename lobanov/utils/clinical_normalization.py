from __future__ import annotations

import re
from difflib import SequenceMatcher

_RU_MONTH_TO_NUMBER = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}

_DRUG_NORMALIZATION_MAP = {
    "нимесил": "Нимесил",
    "не месил": "Нимесил",
    "нимесилу": "Нимесил",
    "пенициллин": "пенициллин",
    "пинцелин": "пенициллин",
}

_DIAGNOSIS_NORMALIZATION_MAP = {
    "цефалгия напряжения": "Цефалгия напряжения",
    "цифалгия напряжения": "Цефалгия напряжения",
}
_SHORT_YEAR_LEN = 2
_TERM_MATCH_THRESHOLD = 0.86
_SOURCE_MATCH_THRESHOLD = 0.72


def safe_normalize_transcript(text: str) -> str:
    normalized = text.replace("—", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s+([.,!?;:])", r"\1", normalized)
    normalized = re.sub(r"([.,!?;:])\1+", r"\1", normalized)
    return normalized.strip()


def normalize_date_value(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip().lower())
    compact = compact.replace("год", "").replace("года", "").strip()

    direct_match = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", compact)
    if direct_match:
        day, month, year = direct_match.groups()
        if len(year) == _SHORT_YEAR_LEN:
            year = f"20{year}"
        return f"{int(day):02d}.{int(month):02d}.{int(year):04d}"

    month_match = re.search(r"(\d{1,2})[-\s]*([а-я]+)[,\s]+(\d{4})", compact)
    if month_match:
        day, month_name, year = month_match.groups()
        month = _RU_MONTH_TO_NUMBER.get(month_name.strip())
        if month:
            return f"{int(day):02d}.{month}.{int(year):04d}"

    return value.strip()


def normalize_gender_value(value: str, allowed_options: list[str] | None = None) -> str:
    normalized = value.strip().lower()
    if normalized in {"мужской", "муж", "male", "мурской"}:
        candidate = "Мужской"
    elif normalized in {"женский", "жен", "female"}:
        candidate = "Женский"
    else:
        candidate = value.strip()

    if allowed_options:
        for option in allowed_options:
            if option.lower() == candidate.lower():
                return option
    return candidate


def normalize_medical_phrase(value: str, mapping: dict[str, str]) -> str:
    cleaned = value.strip()
    lowered = cleaned.lower()
    if lowered in mapping:
        return mapping[lowered]
    for typo, canon in mapping.items():
        if SequenceMatcher(None, lowered, typo).ratio() >= _TERM_MATCH_THRESHOLD:
            return canon
    return cleaned


def normalize_fact_value(field_name: str, value: str, allowed_options: list[str] | None = None) -> str:
    if not value:
        return value

    if field_name in {"birth_date", "visit_date"}:
        return normalize_date_value(value)
    if field_name == "gender":
        return normalize_gender_value(value, allowed_options=allowed_options)
    if field_name in {"allergies", "treatment_plan"}:
        return normalize_medical_phrase(value, _DRUG_NORMALIZATION_MAP)
    if field_name == "diagnosis":
        return normalize_medical_phrase(value, _DIAGNOSIS_NORMALIZATION_MAP)
    return value.strip()


def fuzzy_source_span(text: str, source: str) -> tuple[int, int]:
    if not text or not source:
        return 0, 0

    exact = text.find(source)
    if exact != -1:
        return exact, exact + len(source)

    lowered_text = text.lower()
    lowered_source = source.lower()
    exact_lower = lowered_text.find(lowered_source)
    if exact_lower != -1:
        return exact_lower, exact_lower + len(source)

    source_len = max(len(source), 8)
    best_score = 0.0
    best_start = 0
    for start in range(max(len(text) - source_len + 1, 1)):
        window = text[start : start + source_len + 12]
        score = SequenceMatcher(None, window.lower(), lowered_source).ratio()
        if score > best_score:
            best_score = score
            best_start = start

    if best_score >= _SOURCE_MATCH_THRESHOLD:
        return best_start, min(best_start + len(source), len(text))
    return 0, 0
