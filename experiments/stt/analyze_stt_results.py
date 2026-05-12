# ruff: noqa: T201

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

METRICS: tuple[str, ...] = (
    "elapsed_seconds",
    "cer",
    "wer",
    "bert_score_f1",
    "embedding_cosine",
    "clinical_term_recall",
)

CATEGORY_RANGES: dict[str, tuple[int, int]] = {
    "real_1_10": (1, 10),
    "ii_11_20": (11, 20),
    "solo_21_30": (21, 30),
}

CATEGORY_LABEL_RU: dict[str, str] = {
    "real_1_10": "real_dialog",
    "ii_11_20": "tts_dialog",
    "solo_21_30": "solo_dialog",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_stt_dir() -> Path:
    """Каталог JSON-результатов STT-бенчей (см. experiments/stt/bench_stt.py)."""
    return repo_root() / "experiments" / "results" / "stt"


def results_dir() -> Path:
    """Обратная совместимость: то же, что ``results_stt_dir``."""
    return results_stt_dir()


def iter_stt_bench_json_files() -> list[Path]:
    """JSON результатов STT-бенча: только каталог ``experiments/results/stt``."""
    stt_dir = results_stt_dir()
    if not stt_dir.is_dir():
        return []
    return sorted(stt_dir.glob("bench_*.json"), key=str)


def dialog_index(dialog_id: str) -> int | None:
    text = dialog_id.strip()
    match = re.match(r"^dialog_(\d+)$", text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def detect_category(dialog_id: str) -> str:
    idx = dialog_index(dialog_id)
    if idx is None:
        return "other"
    for key, (lo, hi) in CATEGORY_RANGES.items():
        if lo <= idx <= hi:
            return key
    return "other"


def _parse_recorded_at(value: Any) -> pd.Timestamp:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.Timestamp(0, tz="UTC")
    if isinstance(value, pd.Timestamp):
        return value
    text = str(value).strip()
    if not text:
        return pd.Timestamp(0, tz="UTC")
    parsed = pd.to_datetime(text, utc=True, errors="coerce")
    if pd.isna(parsed):
        return pd.Timestamp(0, tz="UTC")
    if isinstance(parsed, pd.Timestamp):
        return parsed
    return pd.Timestamp(0, tz="UTC")


def _is_number(x: Any) -> bool:
    if x is None:
        return False
    if isinstance(x, bool | str):
        return False
    try:
        float(x)
    except (TypeError, ValueError):
        return False
    else:
        return True


def load_raw_records_from_file(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        msg = f"Expected JSON array in {path}"
        raise TypeError(msg)
    out: list[dict[str, Any]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            msg = f"Expected object at index {i} in {path}"
            raise TypeError(msg)
        row = dict(item)
        row["source_file"] = path.name
        out.append(row)
    return out


def collect_all_records(paths: list[Path] | None = None) -> pd.DataFrame:
    file_list = paths if paths is not None else iter_stt_bench_json_files()
    rows: list[dict[str, Any]] = []
    for path in file_list:
        rows.extend(load_raw_records_from_file(path))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def normalize_successful_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    mask_err = df["error"].isna() | (df["error"] == "")
    work = df.loc[mask_err].copy()
    if work.empty:
        return pd.DataFrame()

    metrics_df = pd.json_normalize(work["metrics"])
    nested_metrics = tuple(name for name in METRICS if name != "elapsed_seconds")
    for name in nested_metrics:
        if name not in metrics_df.columns:
            metrics_df[name] = np.nan
    metrics_df = metrics_df.loc[:, list(nested_metrics)]

    work = work.drop(columns=["metrics"], errors="ignore").reset_index(drop=True)
    metrics_df = metrics_df.reset_index(drop=True)
    work = pd.concat([work, metrics_df], axis=1)

    for name in METRICS:
        if name not in work.columns:
            work[name] = np.nan

    metric_masks = [work[name].map(_is_number) for name in METRICS]
    num_mask = pd.concat(metric_masks, axis=1).all(axis=1)
    work = work.loc[num_mask].copy()
    if work.empty:
        return work

    for name in METRICS:
        work[name] = pd.to_numeric(work[name], errors="coerce")

    work["recorded_at"] = work["recorded_at"].map(_parse_recorded_at)
    work = work.sort_values(["provider", "model", "dialog_id", "recorded_at"])
    work = work.drop_duplicates(subset=["provider", "model", "dialog_id"], keep="last")

    work["category"] = work["dialog_id"].astype(str).map(detect_category)
    work = work.loc[work["category"] != "other"].copy()
    return work.reset_index(drop=True)


def build_summary_table(norm: pd.DataFrame) -> pd.DataFrame:
    if norm.empty:
        return pd.DataFrame(columns=["provider", "model"])

    summary_rows: list[dict[str, Any]] = []
    for (provider, model), group in norm.groupby(["provider", "model"], sort=False):
        row: dict[str, Any] = {"provider": provider, "model": model}
        for cat_key in CATEGORY_RANGES:
            sub = group.loc[group["category"] == cat_key]
            n = len(sub)
            row[f"n_{cat_key}"] = n
            for m in METRICS:
                col = f"{cat_key}__mean_{m}"
                row[col] = float(sub[m].mean()) if n else np.nan

        row["n_overall"] = len(group)
        for m in METRICS:
            row[f"overall__mean_{m}"] = float(group[m].mean()) if len(group) else np.nan
        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def summary_to_excel_columns(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary

    df = summary.copy()
    rename: dict[str, str] = {
        "provider": "Провайдер",
        "model": "Модель",
    }

    for cat_key, label in CATEGORY_LABEL_RU.items():
        rename[f"n_{cat_key}"] = f"n ({label})"

    rename["n_overall"] = "n (всего в 1–30)"

    for cat_key, label in CATEGORY_LABEL_RU.items():
        for m in METRICS:
            old = f"{cat_key}__mean_{m}"
            pretty_m = {
                "elapsed_seconds": "время_с",
                "cer": "cer",
                "wer": "wer",
                "bert_score_f1": "bert_score_f1",
                "embedding_cosine": "embedding_cosine",
                "clinical_term_recall": "clinical_term_recall",
            }[m]
            rename[old] = f"среднее {label} — {pretty_m}"

    for m in METRICS:
        pretty_m = {
            "elapsed_seconds": "время_с",
            "cer": "cer",
            "wer": "wer",
            "bert_score_f1": "bert_score_f1",
            "embedding_cosine": "embedding_cosine",
            "clinical_term_recall": "clinical_term_recall",
        }[m]
        rename[f"overall__mean_{m}"] = f"среднее всего — {pretty_m}"

    out = df.rename(columns=rename)
    first = ["Модель", "Провайдер"]
    rest = [c for c in out.columns if c not in first]
    return out[first + rest]


def save_summary_xlsx(summary: pd.DataFrame, xlsx_path: Path) -> None:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    excel_df = summary_to_excel_columns(summary)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        excel_df.to_excel(writer, sheet_name="summary", index=False)
    print(f"Excel: {xlsx_path}")


def main() -> int:
    paths = iter_stt_bench_json_files()
    if not paths:
        stt = results_stt_dir()
        print(
            f"No STT bench JSON found under {stt}",
            file=sys.stderr,
        )
        return 1

    raw = collect_all_records(paths)
    if raw.empty:
        print("No records loaded from STT bench JSON files.", file=sys.stderr)
        return 1

    norm = normalize_successful_records(raw)
    if norm.empty:
        print("No successful records with complete metrics (after filtering).", file=sys.stderr)
        return 1

    summary = build_summary_table(norm)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_base = results_stt_dir()
    out_base.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_base / f"bench_summary_{ts}.xlsx"
    save_summary_xlsx(summary, xlsx_path)

    print("Done. Charts: uv run python experiments/stt/plot_stt_results.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
