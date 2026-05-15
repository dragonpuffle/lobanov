from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SUMMARY_METRICS: tuple[tuple[str, str], ...] = (
    ("aggregate.field_filling.precision", "ff_precision"),
    ("aggregate.field_filling.recall", "ff_recall"),
    ("aggregate.field_filling.f1", "ff_f1"),
    ("aggregate.field_filling.accuracy", "ff_accuracy"),
    ("aggregate.exact_match_accuracy", "exact_match_accuracy"),
    ("aggregate.mean_token_f1", "mean_token_f1"),
    ("aggregate.mean_bert_score_f1", "mean_bert_score_f1"),
    ("aggregate.mean_embedding_cosine", "mean_embedding_cosine"),
    ("aggregate.mean_rouge_l_f1", "mean_rouge_l_f1"),
)

PER_FIELD_SHEETS: tuple[tuple[str, str, str], ...] = (
    ("pf_exact_match", "exact_match_rate", "exact_match"),
    ("pf_pred_filled", "pred_filled_rate", "pred_filled"),
    ("pf_bert_score_f1", "bert_score_f1_mean", "bert_score_f1"),
    ("pf_token_f1", "token_f1_mean", "token_f1"),
    ("pf_embedding_cosine", "embedding_cosine_mean", "embedding_cosine"),
    ("pf_rouge_l_f1", "rouge_l_f1_mean", "rouge_l_f1"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def nlp_results_dir() -> Path:
    return repo_root() / "experiments" / "results" / "nlp"


def iter_nlp_bench_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(base.glob("bench_nlp_*.json"), key=str)


def _safe_get(obj: dict[str, Any], dotted_key: str) -> Any:
    cursor: Any = obj
    for key in dotted_key.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _as_float_or_nan(value: Any) -> float:
    if value is None or value == "":
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _as_bool(value: Any) -> bool | None:
    result: bool | None = None
    if isinstance(value, bool):
        result = value
    elif value is None:
        result = None
    elif isinstance(value, (int, float)):
        result = None if np.isnan(value) else bool(value)
    else:
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "y"}:
            result = True
        elif text in {"false", "0", "no", "n"}:
            result = False
    return result


def _nanmean_or_nan(values: list[float]) -> float:
    if not values:
        return float("nan")
    arr = np.asarray(values, dtype=float)
    if np.isnan(arr).all():
        return float("nan")
    return float(np.nanmean(arr))


def _resolve_stt_result_path(stt_result_file: str | None) -> Path | None:
    if not stt_result_file:
        return None
    p = Path(str(stt_result_file).strip())
    if not p.parts:
        return None
    return p if p.is_absolute() else (repo_root() / p).resolve()


def _mean_stt_elapsed_seconds_from_json(
    stt_result_file: str | None,
    cache: dict[str, float],
) -> float:
    """Среднее elapsed_seconds по успешным записям STT-бенча (тот же файл, что и stt_result_file в bench_nlp)."""
    path = _resolve_stt_result_path(stt_result_file)
    if path is None:
        return float("nan")
    key = str(path)
    if key in cache:
        return cache[key]
    if not path.is_file():
        cache[key] = float("nan")
        return float("nan")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        cache[key] = float("nan")
        return float("nan")
    data = json.loads(raw)
    if not isinstance(data, list):
        cache[key] = float("nan")
        return float("nan")
    elapsed: list[float] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        err = item.get("error")
        if err is not None and str(err) != "":
            continue
        elapsed.append(_as_float_or_nan(item.get("elapsed_seconds")))
    mean_el = _nanmean_or_nan(elapsed)
    cache[key] = mean_el
    return mean_el


def load_records(path: Path) -> list[dict[str, Any]]:
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


def collect_raw_records(base: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in iter_nlp_bench_files(base):
        rows.extend(load_records(path))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _group_keys(df: pd.DataFrame) -> list[str]:
    for col in ("experiment_id", "provider", "model", "transcript_source", "stt_result_file"):
        if col not in df.columns:
            df[col] = None
    return ["experiment_id", "provider", "model", "transcript_source", "stt_result_file"]


def _build_run_label(
    provider: str,
    model: str,
    transcript_source: str,
    stt_result_file: str | None,
    experiment_id: str,
) -> str:
    source = transcript_source or "unknown"
    if source != "expected" and stt_result_file:
        stt_name = Path(stt_result_file).name
        source = f"{source}:{stt_name}"
    exp_short = experiment_id[:8] if experiment_id else "no-exp"
    return f"{provider} / {model} ({source}) [{exp_short}]"


def build_summary(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    group_cols = _group_keys(raw)
    rows: list[dict[str, Any]] = []
    stt_elapsed_cache: dict[str, float] = {}

    for key_vals, group in raw.groupby(group_cols, dropna=False, sort=True):
        key_map = dict(zip(group_cols, key_vals, strict=True))
        success_mask = group["error"].isna() | (group["error"] == "")
        success = group.loc[success_mask].copy()

        row: dict[str, Any] = {
            **key_map,
            "n_total": len(group),
            "n_success": len(success),
            "n_error": int(len(group) - len(success)),
            "mean_elapsed_seconds": float(success["elapsed_seconds"].mean())
            if "elapsed_seconds" in success.columns and len(success) > 0
            else float("nan"),
        }

        ts = str(row.get("transcript_source") or "").strip().lower()
        stt_file = row.get("stt_result_file")
        stt_file_s = str(stt_file).strip() if stt_file is not None and str(stt_file).strip() else None
        if ts == "stt_result" and stt_file_s:
            mean_stt = _mean_stt_elapsed_seconds_from_json(stt_file_s, stt_elapsed_cache)
        else:
            mean_stt = float("nan")
        row["mean_stt_elapsed_seconds"] = mean_stt

        for dotted_key, out_col in SUMMARY_METRICS:
            values = [
                _as_float_or_nan(_safe_get(m, dotted_key))
                for m in success.get("metrics", pd.Series(dtype=object)).tolist()
                if isinstance(m, dict)
            ]
            row[out_col] = _nanmean_or_nan(values)

        row["run_label"] = _build_run_label(
            provider=str(row.get("provider") or ""),
            model=str(row.get("model") or ""),
            transcript_source=str(row.get("transcript_source") or ""),
            stt_result_file=str(row.get("stt_result_file")) if row.get("stt_result_file") else None,
            experiment_id=str(row.get("experiment_id") or ""),
        )
        rows.append(row)

    summary = pd.DataFrame(rows)
    order = [
        "experiment_id",
        "provider",
        "model",
        "transcript_source",
        "stt_result_file",
        "run_label",
        "n_total",
        "n_success",
        "n_error",
        "mean_elapsed_seconds",
        "mean_stt_elapsed_seconds",
        "ff_precision",
        "ff_recall",
        "ff_f1",
        "ff_accuracy",
        "exact_match_accuracy",
        "mean_token_f1",
        "mean_bert_score_f1",
        "mean_embedding_cosine",
        "mean_rouge_l_f1",
    ]
    return summary.loc[:, [c for c in order if c in summary.columns]]


def _parse_per_field_rows(success_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, rec in success_df.iterrows():
        metrics = rec.get("metrics")
        if not isinstance(metrics, dict):
            continue
        per_field = metrics.get("per_field")
        if not isinstance(per_field, dict):
            continue
        run_label = _build_run_label(
            provider=str(rec.get("provider") or ""),
            model=str(rec.get("model") or ""),
            transcript_source=str(rec.get("transcript_source") or ""),
            stt_result_file=str(rec.get("stt_result_file")) if rec.get("stt_result_file") else None,
            experiment_id=str(rec.get("experiment_id") or ""),
        )
        for field_name, field_data in per_field.items():
            if not isinstance(field_data, dict):
                continue
            gt_filled = _as_bool(field_data.get("gt_filled"))
            pred_filled = _as_bool(field_data.get("pred_filled"))
            exact_match = _as_bool(field_data.get("exact_match"))
            rows.append({
                "run_label": run_label,
                "field_name": str(field_name),
                "gt_filled": gt_filled,
                "pred_filled": pred_filled,
                "exact_match": exact_match,
                "token_f1": _as_float_or_nan(field_data.get("token_f1")),
                "bert_score_f1": _as_float_or_nan(field_data.get("bert_score_f1")),
                "embedding_cosine": _as_float_or_nan(field_data.get("embedding_cosine")),
                "rouge_l_f1": _as_float_or_nan(field_data.get("rouge_l_f1")),
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _aggregate_per_field_metrics(per_field_df: pd.DataFrame) -> pd.DataFrame:
    if per_field_df.empty:
        return pd.DataFrame()

    work = per_field_df.copy()

    if "exact_match" in work.columns:
        em_mask = work["gt_filled"] == True  # noqa: E712
        work["exact_match_rate"] = np.where(
            em_mask,
            work["exact_match"].map(lambda v: 1.0 if v is True else 0.0),
            np.nan,
        )
    if "pred_filled" in work.columns:
        work["pred_filled_rate"] = work["pred_filled"].map(
            lambda v: 1.0 if v is True else (0.0 if v is False else np.nan)
        )

    grouped = work.groupby(["run_label", "field_name"], dropna=False, sort=True)
    agg = grouped.agg(
        exact_match_rate=("exact_match_rate", "mean"),
        pred_filled_rate=("pred_filled_rate", "mean"),
        bert_score_f1_mean=("bert_score_f1", "mean"),
        token_f1_mean=("token_f1", "mean"),
        embedding_cosine_mean=("embedding_cosine", "mean"),
        rouge_l_f1_mean=("rouge_l_f1", "mean"),
    )
    return agg.reset_index()


def build_per_field_sheets(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if raw.empty:
        return {}
    success_mask = raw["error"].isna() | (raw["error"] == "")
    success = raw.loc[success_mask].copy()
    per_field_long = _parse_per_field_rows(success)
    if per_field_long.empty:
        return {}

    agg = _aggregate_per_field_metrics(per_field_long)
    sheets: dict[str, pd.DataFrame] = {}
    for sheet_name, metric_col, _ in PER_FIELD_SHEETS:
        if metric_col not in agg.columns:
            continue
        pivot = (
            agg
            .pivot_table(index="run_label", columns="field_name", values=metric_col, aggfunc="mean")
            .sort_index(axis=0)
            .sort_index(axis=1)
            .reset_index()
        )
        sheets[sheet_name] = pivot
    return sheets


def save_summary_xlsx(
    summary: pd.DataFrame,
    per_field_sheets: dict[str, pd.DataFrame],
    xlsx_path: Path,
) -> None:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="summary", index=False)
        for sheet_name, frame in per_field_sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"Excel: {xlsx_path}")


def main() -> int:
    base = nlp_results_dir()
    if not base.is_dir():
        print(f"NLP results directory not found: {base}", file=sys.stderr)
        return 1

    raw = collect_raw_records(base)
    if raw.empty:
        print(f"No bench_nlp_*.json files found under {base}", file=sys.stderr)
        return 1

    summary = build_summary(raw)
    if summary.empty:
        print("No summary rows could be built.", file=sys.stderr)
        return 1

    per_field_sheets = build_per_field_sheets(raw)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = base / f"bench_nlp_summary_{ts}.xlsx"
    save_summary_xlsx(summary, per_field_sheets, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
