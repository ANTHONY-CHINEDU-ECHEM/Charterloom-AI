"""Report figures rendered with matplotlib.

Colours follow a validated, colour vision deficiency safe categorical order
(blue, orange, aqua) with a single hue sequential ramp for heatmaps. Text uses
neutral ink, never series colours, and every multi series chart carries a legend
plus direct labels.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from charterloom.catalog import ADJUSTMENT_BY_CODE, ARCHETYPE_BY_KEY  # noqa: E402
from charterloom.text import minus  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "charterloom_blue", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])

SHORT_NAMES = {
    "scrum_product_delivery": "Scrum",
    "kanban_continuous_flow": "Kanban",
    "regulated_compliance_pipeline": "Regulated",
    "stage_gate_waterfall": "Stage gate",
    "scaled_release_train": "Release train",
    "dual_track_discovery": "Dual track",
    "scrumban_hybrid": "Scrumban",
    "incident_change_control": "Change control",
}


def _style(ax, title, subtitle=None):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9, length=0)
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, fontweight="bold", pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0.0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=INK_SECONDARY, va="bottom")


def _figure(width, height):
    fig, ax = plt.subplots(figsize=(width, height), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def model_comparison(report, path):
    models = report["recommendation"]["models"]
    names = list(models)
    acc = [models[n]["accuracy"] for n in names]
    f1 = [models[n]["macro_f1"] for n in names]
    fig, ax = _figure(9, 4.6)
    y = np.arange(len(names))
    h = 0.36
    bars_a = ax.barh(y, acc, height=h, color=SERIES[0], label="Accuracy", edgecolor=SURFACE, linewidth=2)
    bars_f = ax.barh(y + h, f1, height=h, color=SERIES[1], label="Macro F1", edgecolor=SURFACE, linewidth=2)
    for bars in (bars_a, bars_f):
        for b in bars:
            ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2, f"{b.get_width():.2f}", va="center",
                    fontsize=8, color=INK_SECONDARY)
    ax.set_yticks(y + h / 2, names)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.08)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=INK_SECONDARY)
    _style(ax, "Workflow recommendation on held out projects",
           f"{report['protocol']['test_high_performing']} held out high performing projects, eight workflow classes")
    return _save(fig, path)


def confusion(report, path):
    cm = np.array(report["recommendation"]["confusion_matrix"]["matrix"], dtype=float)
    labels = [SHORT_NAMES[k] for k in report["recommendation"]["confusion_matrix"]["labels"]]
    norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    fig, ax = _figure(8.2, 6.8)
    ax.imshow(norm, cmap=SEQUENTIAL, vmin=0, vmax=1)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if cm[i, j] > 0:
                ax.text(j, i, f"{norm[i, j]:.0%}\n({int(cm[i, j])})", ha="center", va="center", fontsize=7.2,
                        color="#ffffff" if norm[i, j] > 0.55 else INK)
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Recommended workflow", color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel("Workflow used by the high performing project", color=INK_SECONDARY, fontsize=9)
    _style(ax, "Confusion matrix, row normalised")
    for side in ("bottom",):
        ax.spines[side].set_visible(False)
    return _save(fig, path)


def per_class(report, path):
    data = report["recommendation"]["per_class"]
    keys = sorted(data, key=lambda k: data[k]["f1"])
    fig, ax = _figure(8.4, 4.4)
    vals = [data[k]["f1"] for k in keys]
    bars = ax.barh([SHORT_NAMES[k] for k in keys], vals, color=SERIES[0], height=0.6, edgecolor=SURFACE, linewidth=2)
    for b, k in zip(bars, keys):
        ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2,
                f"{b.get_width():.2f}  (n={data[k]['support']})", va="center", fontsize=8, color=INK_SECONDARY)
    ax.set_xlim(0, 1.15)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    _style(ax, "F1 score by workflow archetype", "Blended recommender, held out high performing projects")
    return _save(fig, path)


def reliability(report, path):
    rows = report["recommendation"]["reliability"]
    fig, ax = _figure(6.4, 5.2)
    ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.6, linestyle=(0, (4, 3)), label="Perfect calibration")
    conf = [r["confidence"] for r in rows]
    acc = [r["accuracy"] for r in rows]
    sizes = [max(20, r["count"] * 1.2) for r in rows]
    ax.plot(conf, acc, color=SERIES[0], linewidth=2, label="Charterloom blended")
    ax.scatter(conf, acc, s=sizes, color=SERIES[0], edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Mean predicted confidence", color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel("Observed accuracy", color=INK_SECONDARY, fontsize=9)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=INK_SECONDARY)
    _style(ax, "Reliability diagram", f"Expected calibration error {report['recommendation']['ece']:.3f}; marker size shows bin count")
    return _save(fig, path)


def grouped(path, title, subtitle, groups, series_names, values, xlim=1.0):
    fig, ax = _figure(9, 4.4)
    x = np.arange(len(groups))
    width = 0.8 / len(series_names)
    for s, name in enumerate(series_names):
        bars = ax.bar(x + s * width, values[s], width=width, color=SERIES[s], label=name, edgecolor=SURFACE, linewidth=2)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012, f"{b.get_height():.2f}", ha="center",
                    fontsize=7.6, color=INK_SECONDARY)
    ax.set_xticks(x + width * minus(len(series_names), 1) / 2, groups)
    ax.set_ylim(0, xlim * 1.12)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="upper right", ncol=len(series_names))
    _style(ax, title, subtitle)
    return _save(fig, path)


def retrieval(report, path):
    data = report["retrieval"]
    names = list(data)
    metrics = [("precision_at_5", "Precision at 5"), ("mrr", "MRR"), ("ndcg_at_10", "nDCG at 10")]
    values = [[data[n][m] for m, _ in metrics] for n in names]
    return grouped(path, "Precedent retrieval quality",
                   "Relevant precedent: same workflow and high performing; index excludes every held out project",
                   [label for _, label in metrics], names, values)


def adjustments(report, path):
    data = report["customization"]
    names = list(data)
    metrics = [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1")]
    values = [[data[n][m] for m, _ in metrics] for n in names]
    return grouped(path, "Workflow adjustment selection",
                   "Applied adjustments versus the adjustments each held out project needed",
                   [label for _, label in metrics], names, values)


def adjustment_codes(report, path):
    per = report["customization"]["Charterloom evidence plus priors"]["per_adjustment"]
    codes = sorted(per, key=lambda c: per[c]["f1"])
    fig, ax = _figure(8.6, 5.6)
    bars = ax.barh([ADJUSTMENT_BY_CODE[c].title for c in codes], [per[c]["f1"] for c in codes], color=SERIES[0],
                   height=0.62, edgecolor=SURFACE, linewidth=2)
    for b, c in zip(bars, codes):
        ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2, f"{b.get_width():.2f}  (n={per[c]['support']})",
                va="center", fontsize=7.8, color=INK_SECONDARY)
    ax.set_xlim(0, 1.18)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    _style(ax, "F1 by workflow adjustment", "Evidence plus priors customizer, held out projects")
    return _save(fig, path)


def knowledge_base(manifest, path):
    counts = manifest["adopted_workflow_counts"]
    high = manifest["high_performing_workflow_counts"]
    keys = sorted(counts, key=counts.get)
    fig, ax = _figure(8.6, 4.6)
    hp = [high.get(k, 0) for k in keys]
    rest = [minus(counts[k], high.get(k, 0)) for k in keys]
    labels = [SHORT_NAMES[k] for k in keys]
    ax.barh(labels, hp, color=SERIES[0], height=0.62, label="High performing", edgecolor=SURFACE, linewidth=2)
    ax.barh(labels, rest, left=hp, color=SERIES[1], height=0.62, label="Below median outcome", edgecolor=SURFACE,
            linewidth=2)
    for i, k in enumerate(keys):
        ax.text(counts[k] + 6, i, f"{counts[k]}", va="center", fontsize=8, color=INK_SECONDARY)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="lower right")
    _style(ax, "Historical projects by adopted workflow",
           f"{manifest['projects']} projects, {manifest['synthetic_words']:,} words of blueprints and post mortems")
    return _save(fig, path)


def architecture(path):
    """Pipeline overview: knowledge base, retrieval, three expert head, customizer, outputs."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(12, 5.4), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    boxes = {
        "charter": (0.2, 2.2, "Project charter", "free text requirements"),
        "features": (2.6, 3.6, "Feature extractor", "signals, team, regimes"),
        "embed": (2.6, 0.8, "Semantic embedder", "TF IDF plus LSA"),
        "kb": (2.6, 2.2, "Knowledge base", "blueprints, post mortems,\nmethodologies, templates"),
        "retriever": (5.0, 0.8, "Hybrid retriever", "BM25 plus dense, RRF"),
        "project": (5.0, 3.6, "Project space index", "nearest precedents"),
        "head": (7.4, 3.6, "Recommendation head", "semantic, structural,\nprecedent experts"),
        "custom": (7.4, 0.8, "Customizer", "params, overlays,\nevidence adjustments"),
        "out": (9.8, 2.2, "Validated workflow", "state machine JSON,\nrationale, citations"),
    }
    w, h = 2.0, 1.05
    tones = {"charter": "#E8EEF7", "kb": "#D3EFDA", "out": "#D3EFDA", "head": "#FCE9C8", "custom": "#FCE9C8"}
    for key, (x, y, title, sub) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=tones.get(key, "#E3D9F2"), edgecolor="#1F2A44", linewidth=1.0))
        ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center", fontsize=9, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=7, color=INK_SECONDARY)
    edges = [("charter", "features"), ("charter", "embed"), ("kb", "retriever"), ("kb", "project"),
             ("embed", "retriever"), ("features", "project"), ("embed", "project"), ("project", "head"),
             ("retriever", "custom"), ("project", "custom"), ("head", "custom"),
             ("custom", "out"), ("head", "out")]
    for a, b in edges:
        xa, ya, *_ = boxes[a]
        xb, yb, *_ = boxes[b]
        start = (xa + w, ya + h / 2) if xb > xa else (xa + w / 2, ya + (h if yb > ya else 0))
        end = (xb, yb + h / 2) if xb > xa else (xb + w / 2, yb + (0 if yb > ya else h))
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="simple,head_width=4,head_length=5,tail_width=0.4",
                                     color="#1F4E8C", alpha=0.75, mutation_scale=1.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0.4, 5.1)
    ax.axis("off")
    ax.set_title("Charterloom AI pipeline", loc="left", fontsize=12.5, fontweight="bold", color=INK)
    return _save(fig, path)


def render_all(report, figures_dir, kb_manifest_path=None):
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    produced = [
        architecture(figures_dir / "architecture.png"),
        model_comparison(report, figures_dir / "model_comparison.png"),
        confusion(report, figures_dir / "confusion_matrix.png"),
        per_class(report, figures_dir / "per_class_f1.png"),
        reliability(report, figures_dir / "reliability_diagram.png"),
        retrieval(report, figures_dir / "retrieval_quality.png"),
        adjustments(report, figures_dir / "adjustment_selection.png"),
        adjustment_codes(report, figures_dir / "adjustment_f1_by_code.png"),
    ]
    if kb_manifest_path and Path(kb_manifest_path).exists():
        manifest = json.loads(Path(kb_manifest_path).read_text(encoding="utf8"))
        produced.append(knowledge_base(manifest, figures_dir / "knowledge_base_composition.png"))
    return produced


def archetype_label(key):
    return ARCHETYPE_BY_KEY[key].display_name
