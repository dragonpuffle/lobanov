from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_EXP_DIR = Path(__file__).resolve().parent
if str(_EXP_DIR) not in sys.path:
    sys.path.insert(0, str(_EXP_DIR))

from analyze_stt_results import (  # noqa: E402
    CATEGORY_LABEL_RU,
    CATEGORY_RANGES,
    METRICS,
    build_summary_table,
    collect_all_records,
    iter_stt_bench_json_files,
    normalize_successful_records,
    results_stt_dir,
)

OVERALL_ONLY_METRICS: tuple[tuple[str, str, str], ...] = (
    ("cer", "CER", "bars_overall_cer.png"),
    ("wer", "WER", "bars_overall_wer.png"),
    ("elapsed_seconds", "Время, с", "bars_overall_time.png"),
    ("embedding_cosine", "embedding cosine", "bars_overall_embedding_cosine.png"),
    ("bert_score_f1", "BERTScore F1", "bars_overall_bertscore.png"),
    ("clinical_term_recall", "clinical term recall", "bars_overall_clinical_term_recall.png"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def stt_plots_root() -> Path:
    return repo_root() / "experiments" / "plots" / "stt"


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


def plot_radar_overall_metrics(summary: pd.DataFrame, out_dir: Path) -> None:
    """Radar chart по overall-метрикам STT; для ошибок используем 1-CER и 1-WER."""
    if summary.empty:
        return

    required = (
        "overall__mean_cer",
        "overall__mean_wer",
        "overall__mean_bert_score_f1",
        "overall__mean_embedding_cosine",
        "overall__mean_clinical_term_recall",
    )
    if any(col not in summary.columns for col in required):
        return

    categories = [
        "1-CER",
        "1-WER",
        "bert_score_f1",
        "embedding_cosine",
        "clinical_term_recall",
    ]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8.5, 7.0), subplot_kw={"polar": True})
    n_pts = len(summary)
    cmap = plt.get_cmap("tab20") if n_pts <= 20 else plt.get_cmap("gist_ncar")  # noqa: PLR2004

    for i, (_, row) in enumerate(summary.iterrows()):
        values = [
            1.0 - float(row["overall__mean_cer"]),
            1.0 - float(row["overall__mean_wer"]),
            float(row["overall__mean_bert_score_f1"]),
            float(row["overall__mean_embedding_cosine"]),
            float(row["overall__mean_clinical_term_recall"]),
        ]
        values = [float(np.clip(v, 0.0, 1.0)) for v in values]
        values += values[:1]

        color = cmap(i / max(n_pts - 1, 1))
        lab = f"{row['provider']} · {row['model']}".replace("/", " ⁄ ")
        ax.plot(angles, values, linewidth=1.4, color=color, label=lab[:120])
        ax.fill(angles, values, color=color, alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0.0, 1.0)
    ax.grid(alpha=0.25)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0,
        fontsize=7,
        framealpha=0.92,
        ncol=1,
    )

    dest = out_dir / "radar_all_metrics.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    plt.title("Overall STT metrics radar (1-CER, 1-WER)")
    plt.tight_layout()
    plt.savefig(dest, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot: {dest}")


def generate_all_plots(summary: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_overall_single_metric_barh(summary, out_dir)
    for m in METRICS:
        plot_single_metric_bars(summary, m, out_dir)
    plot_radar_overall_metrics(summary, out_dir)
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
    paths = iter_stt_bench_json_files()
    if not paths:
        stt = results_stt_dir()
        print(f"No STT bench JSON found under {stt}", file=sys.stderr)
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
    out_dir = stt_plots_root()
    generate_all_plots(summary, out_dir)
    print(f"Done. Plots: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
