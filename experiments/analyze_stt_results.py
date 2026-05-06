# ruff: noqa: T201

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
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

OVERALL_ONLY_METRICS: tuple[tuple[str, str, str], ...] = (
    ("cer", "CER", "bars_overall_cer.png"),
    ("wer", "WER", "bars_overall_wer.png"),
    ("elapsed_seconds", "Время, с", "bars_overall_time.png"),
    ("embedding_cosine", "embedding cosine", "bars_overall_embedding_cosine.png"),
    ("bert_score_f1", "BERTScore F1", "bars_overall_bertscore.png"),
    ("clinical_term_recall", "clinical term recall", "bars_overall_clinical_term_recall.png"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def results_dir() -> Path:
    return repo_root() / "experiments" / "results"


def plots_dir() -> Path:
    return repo_root() / "experiments" / "plots"


def iter_bench_json_files(base: Path):
    yield from sorted(base.glob("bench_*.json"))


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


def collect_all_records(base: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in iter_bench_json_files(base):
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


def _model_tick_labels(summary: pd.DataFrame) -> list[str]:
    labels: list[str] = []
    for _, row in summary.iterrows():
        prov = str(row["provider"])
        mdl = str(row["model"])
        labels.append(f"{prov}\n{mdl}")
    return labels


def _configure_vertical_bar_xtick_labels(ax: plt.Axes, summary: pd.DataFrame) -> None:
    ax.set_xticks(np.arange(len(summary)))
    ax.set_xticklabels(_model_tick_labels(summary), fontsize=7)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=68, ha="right")
    ax.tick_params(axis="x", pad=2)


def _save_current_figure(path: Path, title: str, *, use_tight_layout: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.title(title)
    if use_tight_layout:
        plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Plot: {path}")


def plot_overall_single_metric_barh(summary: pd.DataFrame, out_dir: Path) -> None:
    """Столбиковые графики: одна метрика по overall (диалоги 1–30), один бар на модель (горизонтально для читаемых подписей)."""
    if summary.empty:
        return

    y_labels = [f"{r['provider']!s} → {str(r['model']).replace('/', ' ⁄ ')}"[:88] for _, r in summary.iterrows()]
    height = max(5.5, len(summary) * 0.35)
    for metric_key, y_title, fname in OVERALL_ONLY_METRICS:
        col = f"overall__mean_{metric_key}"
        if col not in summary.columns:
            continue

        vals = summary[col].to_numpy(dtype=float)
        y_pos = np.arange(len(summary))[::-1]
        fig_h = plt.figure(figsize=(9.5, height))
        ax = fig_h.add_subplot(111)
        ax.barh(y_pos, vals, height=0.65, alpha=0.9)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(y_labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel(y_title)
        ax.grid(axis="x", alpha=0.25)
        out_path = out_dir / fname
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.title(f"Overall (1–30): {y_title}")
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig_h)
        print(f"Plot: {out_path}")


def plot_single_metric_bars(
    summary: pd.DataFrame,
    metric: str,
    out_dir: Path,
) -> None:
    if summary.empty:
        return

    x = np.arange(len(summary))
    width = 0.25
    fig = plt.figure(figsize=(max(10.0, len(summary) * 0.55), 5.8), layout="constrained")
    ax = fig.add_subplot(111)

    series = [("overall", "всего")]
    series.extend((k, CATEGORY_LABEL_RU[k]) for k in CATEGORY_RANGES)

    for j, (prefix, lab) in enumerate(series):
        col = f"overall__mean_{metric}" if prefix == "overall" else f"{prefix}__mean_{metric}"
        offset = (j - len(series) / 2) * width
        ax.bar(x + offset, summary[col].to_numpy(dtype=float), width=width, label=lab)

    ax.set_xticks(x)
    _configure_vertical_bar_xtick_labels(ax, summary)
    ax.set_ylabel(metric)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    safe = metric.replace("/", "_")
    _save_current_figure(
        out_dir / f"bars_by_category_{safe}.png",
        f"{metric}: сравнение категорий",
        use_tight_layout=False,
    )


def plot_scatter(summary: pd.DataFrame, x_col: str, y_col: str, out_name: str, out_dir: Path) -> None:
    if summary.empty:
        return
    if x_col not in summary.columns or y_col not in summary.columns:
        return

    n_pts = len(summary)
    cmap = plt.get_cmap("tab20") if n_pts <= 20 else plt.get_cmap("gist_ncar")  # noqa: PLR2004

    fig, ax = plt.subplots(figsize=(7.5, 5.25))
    for i, (_, row) in enumerate(summary.iterrows()):
        color = cmap(i / max(n_pts - 1, 1))
        lab = f"{row['provider']} · {row['model']}".replace("/", " ⁄ ")
        ax.scatter(
            float(row[x_col]),
            float(row[y_col]),
            s=72,
            alpha=0.92,
            color=color,
            label=lab[:120],
            edgecolors="black",
            linewidths=0.35,
            zorder=3,
        )
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.grid(alpha=0.25, zorder=0)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0,
        fontsize=7,
        framealpha=0.92,
        ncol=1,
    )
    ax.set_title(f"{y_col} vs {x_col}")
    plt.tight_layout()
    dest = out_dir / out_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(dest, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot: {dest}")


def generate_all_plots(summary: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_overall_single_metric_barh(summary, out_dir)
    for m in METRICS:
        plot_single_metric_bars(summary, m, out_dir)
    plot_scatter(
        summary,
        "overall__mean_elapsed_seconds",
        "overall__mean_wer",
        "scatter_overall_wer_vs_time.png",
        out_dir,
    )
    plot_scatter(
        summary,
        "overall__mean_elapsed_seconds",
        "overall__mean_cer",
        "scatter_overall_cer_vs_time.png",
        out_dir,
    )
    plot_scatter(
        summary,
        "overall__mean_embedding_cosine",
        "overall__mean_bert_score_f1",
        "scatter_overall_bertf1_vs_emb_cos.png",
        out_dir,
    )
    plot_scatter(
        summary,
        "overall__mean_elapsed_seconds",
        "overall__mean_embedding_cosine",
        "scatter_overall_emb_cosine_vs_time.png",
        out_dir,
    )
    plot_scatter(
        summary,
        "overall__mean_elapsed_seconds",
        "overall__mean_bert_score_f1",
        "scatter_overall_bertf1_vs_time.png",
        out_dir,
    )


def main() -> int:
    base = results_dir()
    if not base.is_dir():
        print(f"Results directory not found: {base}", file=sys.stderr)
        return 1

    raw = collect_all_records(base)
    if raw.empty:
        print(f"No bench_*.json files found under {base}", file=sys.stderr)
        return 1

    norm = normalize_successful_records(raw)
    if norm.empty:
        print("No successful records with complete metrics (after filtering).", file=sys.stderr)
        return 1

    summary = build_summary_table(norm)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    xlsx_path = base / f"bench_summary_{ts}.xlsx"
    save_summary_xlsx(summary, xlsx_path)

    plots = plots_dir()
    generate_all_plots(summary, plots)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
