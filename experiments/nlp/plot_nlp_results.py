from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TEXT_METRIC_COLS: tuple[str, ...] = (
    "mean_token_f1",
    "mean_bert_score_f1",
    "mean_embedding_cosine",
    "mean_rouge_l_f1",
)

RADAR_COLS: tuple[str, ...] = (
    "ff_precision",
    "ff_recall",
    "exact_match_accuracy",
    "mean_token_f1",
    "mean_bert_score_f1",
    "mean_embedding_cosine",
    "mean_rouge_l_f1",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def nlp_results_dir() -> Path:
    return repo_root() / "experiments" / "results" / "nlp"


def nlp_plots_root() -> Path:
    return repo_root() / "experiments" / "plots" / "nlp"


def _model_label(row: pd.Series) -> str:
    provider = str(row.get("provider", ""))
    model = str(row.get("model", ""))
    return f"{provider}\n{model}"


def _run_label(row: pd.Series) -> str:
    label = str(row.get("run_label", "")).strip()
    if label:
        return label
    source = str(row.get("transcript_source", "")).strip() or "unknown"
    return f"{row.get('provider', '')} / {row.get('model', '')} ({source})"


def _ensure_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _wrap_heatmap_label(text: str, *, width: int) -> str:
    s = str(text).strip()
    if not s:
        return ""
    lines = textwrap.wrap(s, width=width, break_long_words=True)
    return "\n".join(lines) if lines else s


def _save_fig(path: Path, *, title: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if title:
        plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"Plot: {path}")


def load_latest_summary_xlsx(base: Path) -> Path:
    files = sorted(base.glob("bench_nlp_summary_*.xlsx"), key=str)
    if not files:
        msg = f"No bench_nlp_summary_*.xlsx found in {base}"
        raise FileNotFoundError(msg)
    return files[-1]


def _read_sheet_if_exists(xlsx_path: Path, sheet_name: str) -> pd.DataFrame:
    xls = pd.ExcelFile(xlsx_path)
    if sheet_name not in xls.sheet_names:
        return pd.DataFrame()
    return pd.read_excel(xlsx_path, sheet_name=sheet_name)


def load_workbook_frames(xlsx_path: Path) -> dict[str, pd.DataFrame]:
    sheet_names = (
        "summary",
        "pf_exact_match",
        "pf_pred_filled",
        "pf_bert_score_f1",
        "pf_token_f1",
        "pf_embedding_cosine",
        "pf_rouge_l_f1",
    )
    return {name: _read_sheet_if_exists(xlsx_path, name) for name in sheet_names}


def split_summary_by_source(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if summary.empty:
        return summary, summary
    src = summary["transcript_source"].astype(str).str.strip().str.lower()
    expected = summary.loc[src == "expected"].copy()
    non_expected = summary.loc[src != "expected"].copy()
    return expected, non_expected


def _bar_grouped(
    data: pd.DataFrame,
    metric_cols: list[str],
    out_path: Path,
    *,
    ylabel: str,
    title: str,
) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, metric_cols).copy()
    x = np.arange(len(work))
    width = 0.8 / max(len(metric_cols), 1)
    fig = plt.figure(figsize=(max(11.0, len(work) * 0.85), 6))
    ax = fig.add_subplot(111)
    for i, col in enumerate(metric_cols):
        if col not in work.columns:
            continue
        vals = work[col].to_numpy(dtype=float)
        ax.bar(x + (i - (len(metric_cols) - 1) / 2.0) * width, vals, width=width, label=col)
    ax.set_xticks(x)
    ax.set_xticklabels([_model_label(r) for _, r in work.iterrows()], rotation=65, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0.0, 1.05 if ylabel != "seconds" else None)
    ax.legend(fontsize=8, ncol=min(4, len(metric_cols)))
    _save_fig(out_path, title=title)


def plot_filling_bars(data: pd.DataFrame, out_dir: Path) -> None:
    _bar_grouped(
        data,
        ["ff_precision", "ff_recall", "ff_f1"],
        out_dir / "bars_filling_prec_recall_f1.png",
        ylabel="score",
        title="Field filling: precision / recall / f1",
    )


def plot_filling_accuracy(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, ["ff_accuracy"]).copy()
    x = np.arange(len(work))
    _, ax = plt.subplots(figsize=(max(10.0, len(work) * 0.75), 5.6))
    ax.bar(x, work["ff_accuracy"].to_numpy(dtype=float), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([_model_label(r) for _, r in work.iterrows()], rotation=65, ha="right", fontsize=8)
    ax.set_ylabel("accuracy")
    ax.set_ylim(0.0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    _save_fig(out_dir / "bars_filling_accuracy.png", title="Field filling accuracy")


def plot_text_metrics(data: pd.DataFrame, out_dir: Path) -> None:
    _bar_grouped(
        data,
        list(TEXT_METRIC_COLS),
        out_dir / "bars_text_metrics.png",
        ylabel="score",
        title="Text quality metrics",
    )


def plot_exact_match(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, ["exact_match_accuracy"]).copy()
    x = np.arange(len(work))
    _, ax = plt.subplots(figsize=(max(10.0, len(work) * 0.75), 5.6))
    ax.bar(x, work["exact_match_accuracy"].to_numpy(dtype=float), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([_model_label(r) for _, r in work.iterrows()], rotation=65, ha="right", fontsize=8)
    ax.set_ylabel("exact_match_accuracy")
    ax.set_ylim(0.0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    _save_fig(out_dir / "bars_exact_match.png", title="Exact match accuracy")


def plot_elapsed(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty or "mean_elapsed_seconds" not in data.columns:
        return
    work = _ensure_numeric(data, ["mean_elapsed_seconds"]).copy()
    x = np.arange(len(work))
    _, ax = plt.subplots(figsize=(max(10.0, len(work) * 0.75), 5.6))
    ax.bar(x, work["mean_elapsed_seconds"].to_numpy(dtype=float), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([_model_label(r) for _, r in work.iterrows()], rotation=65, ha="right", fontsize=8)
    ax.set_ylabel("seconds")
    ax.grid(axis="y", alpha=0.25)
    _save_fig(out_dir / "bars_elapsed.png", title="Mean elapsed seconds")


def plot_radar(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, list(RADAR_COLS)).copy()
    categories = list(RADAR_COLS)
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    _, ax = plt.subplots(figsize=(8.4, 7.2), subplot_kw={"polar": True})
    for _, row in work.iterrows():
        values = [float(row.get(c, np.nan)) for c in categories]
        values = [0.0 if np.isnan(v) else max(0.0, min(1.0, v)) for v in values]
        values += values[:1]
        label = f"{row.get('provider', '')} / {row.get('model', '')}"
        ax.plot(angles, values, linewidth=1.4, label=label[:100])
        ax.fill(angles, values, alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0.0, 1.0)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.1, 1.05), fontsize=7, framealpha=0.9)
    _save_fig(out_dir / "radar_all_metrics.png", title="Radar: aggregate metrics")


def _filter_per_field_sheet(
    sheet: pd.DataFrame,
    run_labels: set[str],
) -> pd.DataFrame:
    if sheet.empty or "run_label" not in sheet.columns:
        return pd.DataFrame()
    out = sheet.loc[sheet["run_label"].astype(str).isin(run_labels)].copy()
    if out.empty:
        return out
    return out.set_index("run_label")


def _plot_heatmap(
    sheet: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    vmin: float = 0.0,
    vmax: float = 1.0,
) -> None:
    if sheet.empty:
        return
    values = sheet.to_numpy(dtype=float)
    y_labels = [_wrap_heatmap_label(str(r), width=42) for r in sheet.index]
    y_lines = max(lbl.count("\n") + 1 for lbl in y_labels) if y_labels else 1
    fig_w = max(9.0, sheet.shape[1] * 0.8)
    fig_h = max(4.5, sheet.shape[0] * (0.55 + 0.22 * (y_lines - 1)))
    _, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(values, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(sheet.shape[1]))
    ax.set_xticklabels(list(sheet.columns), rotation=55, ha="right", fontsize=8)
    ax.set_yticks(np.arange(sheet.shape[0]))
    ax.set_yticklabels(y_labels, fontsize=7)
    cbar = plt.colorbar(im, ax=ax)
    cbar.ax.tick_params(labelsize=8)
    _save_fig(out_path, title=title)


def plot_heatmaps(
    run_labels: set[str],
    frames: dict[str, pd.DataFrame],
    out_dir: Path,
) -> None:
    exact = _filter_per_field_sheet(frames.get("pf_exact_match", pd.DataFrame()), run_labels)
    bert = _filter_per_field_sheet(frames.get("pf_bert_score_f1", pd.DataFrame()), run_labels)
    pred = _filter_per_field_sheet(frames.get("pf_pred_filled", pd.DataFrame()), run_labels)
    _plot_heatmap(exact, out_dir / "heatmap_exact_match.png", title="Per-field exact match")
    _plot_heatmap(bert, out_dir / "heatmap_bert_score.png", title="Per-field BERTScore F1")
    _plot_heatmap(pred, out_dir / "heatmap_pred_filled.png", title="Per-field pred_filled rate")


def plot_scatter_f1_vs_elapsed(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, ["ff_f1", "mean_elapsed_seconds"]).dropna(subset=["ff_f1", "mean_elapsed_seconds"])
    if work.empty:
        return
    _, ax = plt.subplots(figsize=(7.6, 5.8))
    for _, row in work.iterrows():
        x = float(row["mean_elapsed_seconds"])
        y = float(row["ff_f1"])
        label = f"{row.get('provider', '')} / {row.get('model', '')}"
        ax.scatter(x, y, s=74, alpha=0.92)
        ax.annotate(label[:56], (x, y), xytext=(5, 3), textcoords="offset points", fontsize=7)
    ax.set_xlabel("mean_elapsed_seconds")
    ax.set_ylabel("ff_f1")
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.25)
    _save_fig(out_dir / "scatter_f1_vs_elapsed.png", title="F1 vs elapsed seconds")


def plot_scatter_bertscore_vs_elapsed(data: pd.DataFrame, out_dir: Path) -> None:
    if data.empty:
        return
    work = _ensure_numeric(data, ["mean_bert_score_f1", "mean_elapsed_seconds"]).dropna(
        subset=["mean_bert_score_f1", "mean_elapsed_seconds"]
    )
    if work.empty:
        return
    _, ax = plt.subplots(figsize=(7.6, 5.8))
    for _, row in work.iterrows():
        x = float(row["mean_elapsed_seconds"])
        y = float(row["mean_bert_score_f1"])
        label = f"{row.get('provider', '')} / {row.get('model', '')}"
        ax.scatter(x, y, s=74, alpha=0.92)
        ax.annotate(label[:56], (x, y), xytext=(5, 3), textcoords="offset points", fontsize=7)
    ax.set_xlabel("mean_elapsed_seconds")
    ax.set_ylabel("mean_bert_score_f1")
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.25)
    _save_fig(out_dir / "scatter_bertscore_f1_vs_elapsed.png", title="BERTScore F1 vs elapsed seconds")


def _aggregate_for_cross_source(summary: pd.DataFrame, source_group: str) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    src = summary["transcript_source"].astype(str).str.strip().str.lower()
    mask = src == "expected" if source_group == "expected" else src != "expected"
    part = summary.loc[mask].copy()
    if part.empty:
        return pd.DataFrame()
    part = _ensure_numeric(part, ["ff_f1"])
    return (
        part
        .groupby(["provider", "model"], as_index=False, dropna=False)["ff_f1"]
        .mean()
        .rename(columns={"ff_f1": "ff_f1_mean"})
    )


def plot_cross_source(summary: pd.DataFrame, out_root: Path) -> None:
    expected = _aggregate_for_cross_source(summary, source_group="expected")
    stt = _aggregate_for_cross_source(summary, source_group="non_expected")
    if expected.empty or stt.empty:
        return

    merged = expected.merge(stt, on=["provider", "model"], how="inner", suffixes=("_expected", "_stt"))
    if merged.empty:
        return

    x = np.arange(len(merged))
    width = 0.38
    _, ax = plt.subplots(figsize=(max(10.0, len(merged) * 0.85), 5.8))
    ax.bar(x - width / 2, merged["ff_f1_mean_expected"].to_numpy(dtype=float), width=width, label="expected")
    ax.bar(x + width / 2, merged["ff_f1_mean_stt"].to_numpy(dtype=float), width=width, label="non_expected")
    labels = [f"{r['provider']}\n{r['model']}" for _, r in merged.iterrows()]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=8)
    ax.set_ylabel("ff_f1")
    ax.set_ylim(0.0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    _save_fig(out_root / "bars_cross_source_f1.png", title="FF F1: expected vs non-expected")

    _, ax = plt.subplots(figsize=(7.8, 5.8))
    ax.scatter(
        merged["ff_f1_mean_expected"].to_numpy(dtype=float),
        merged["ff_f1_mean_stt"].to_numpy(dtype=float),
        s=84,
        alpha=0.9,
    )
    for _, row in merged.iterrows():
        x0 = float(row["ff_f1_mean_expected"])
        y0 = float(row["ff_f1_mean_stt"])
        ax.annotate(
            f"{row['provider']} / {row['model']}"[:65], (x0, y0), xytext=(5, 3), textcoords="offset points", fontsize=7
        )
    ax.set_xlabel("expected_ff_f1")
    ax.set_ylabel("non_expected_ff_f1")
    ax.set_xlim(0.0, 1.05)
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.25)
    _save_fig(out_root / "scatter_expected_vs_stt_f1.png", title="Expected vs non-expected FF F1")


def plot_group(
    summary_group: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    out_dir: Path,
) -> None:
    if summary_group.empty:
        return
    work = summary_group.sort_values(["provider", "model", "experiment_id"], na_position="last").copy()
    plot_filling_bars(work, out_dir)
    plot_filling_accuracy(work, out_dir)
    plot_text_metrics(work, out_dir)
    plot_exact_match(work, out_dir)
    plot_elapsed(work, out_dir)
    plot_radar(work, out_dir)
    run_labels = {str(x) for x in work["run_label"].dropna().tolist()}
    plot_heatmaps(run_labels, frames, out_dir)
    plot_scatter_f1_vs_elapsed(work, out_dir)
    plot_scatter_bertscore_vs_elapsed(work, out_dir)


def main() -> int:
    base = nlp_results_dir()
    if not base.is_dir():
        print(f"NLP results directory not found: {base}", file=sys.stderr)
        return 1

    try:
        xlsx_path = load_latest_summary_xlsx(base)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    frames = load_workbook_frames(xlsx_path)
    summary = frames.get("summary", pd.DataFrame())
    if summary.empty:
        print(f"Summary sheet is empty in {xlsx_path}", file=sys.stderr)
        return 1

    if "run_label" not in summary.columns:
        summary["run_label"] = summary.apply(_run_label, axis=1)

    expected, non_expected = split_summary_by_source(summary)

    out_root = nlp_plots_root()
    plot_group(expected, frames, out_root / "expected")
    plot_group(non_expected, frames, out_root / "stt")
    plot_cross_source(summary, out_root)

    print(f"Done. Source workbook: {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
