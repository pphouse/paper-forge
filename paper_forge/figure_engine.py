"""Generalized figure generation engine for academic papers.

Produces publication-quality figures from declarative JSON/dict specs.
Supports multiple figure types, colorblind-safe palettes, dual PDF/PNG
output, and multi-panel layouts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import seaborn as sns

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_PALETTES_FILE = _ASSETS_DIR / "color_palettes.json"

# ---------------------------------------------------------------------------
# Supported figure types
# ---------------------------------------------------------------------------
SUPPORTED_TYPES = frozenset(
    {
        "bar",
        "barh",
        "line",
        "scatter",
        "heatmap",
        "pie",
        "roc_curve",
        "pr_curve",
        "confusion_matrix",
        "tsne",
        "violin",
        "box",
        "network",
        "multi_panel",
    }
)

# ---------------------------------------------------------------------------
# Publication-quality rcParams
# ---------------------------------------------------------------------------
_PUB_RCPARAMS: dict[str, Any] = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
    "legend.title_fontsize": 8,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
    "lines.linewidth": 1.5,
    "lines.markersize": 5,
    "pdf.fonttype": 42,  # TrueType — required by most journals
    "ps.fonttype": 42,
}


def _load_palettes() -> dict[str, dict[str, str]]:
    """Load colour palettes from the bundled JSON asset."""
    try:
        with open(_PALETTES_FILE) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Could not load colour palettes (%s); using fallback.", exc)
        return {
            "colorblind_safe": {
                "blue": "#0072B2",
                "orange": "#E69F00",
                "green": "#009E73",
                "yellow": "#F0E442",
                "sky_blue": "#56B4E9",
                "vermillion": "#D55E00",
                "purple": "#CC79A7",
            }
        }


class FigureEngine:
    """Create publication-quality figures from declarative specs.

    Parameters
    ----------
    palette_name : str
        Key into *assets/color_palettes.json* (default ``"colorblind_safe"``).
    extra_rcparams : dict | None
        Additional matplotlib rcParams merged on top of the publication
        defaults.
    """

    def __init__(
        self,
        palette_name: str = "colorblind_safe",
        extra_rcparams: dict[str, Any] | None = None,
    ) -> None:
        self._palettes = _load_palettes()
        self.palette_name = palette_name
        self._colors = self._resolve_palette(palette_name)

        # Merge rcParams
        self._rcparams = {**_PUB_RCPARAMS}
        if extra_rcparams:
            self._rcparams.update(extra_rcparams)

    # ------------------------------------------------------------------
    # Palette helpers
    # ------------------------------------------------------------------
    def _resolve_palette(self, name: str) -> list[str]:
        palette = self._palettes.get(name, self._palettes.get("colorblind_safe", {}))
        return list(palette.values())

    @property
    def colors(self) -> list[str]:
        """Active colour cycle as a list of hex strings."""
        return list(self._colors)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_figure(self, fig_spec: dict) -> str:
        """Render a single figure from *fig_spec* and return the output path.

        Required keys in *fig_spec*:

        * ``type`` — one of :data:`SUPPORTED_TYPES`
        * ``data`` — type-specific payload (see individual ``_draw_*`` methods)
        * ``output`` — file stem **or** full path (extensions added automatically)

        Optional keys:

        * ``title``, ``xlabel``, ``ylabel``
        * ``figsize`` — ``[width, height]`` in inches (default ``[6, 4]``)
        * ``style`` — dict of overrides passed to the drawing function
        * ``panel_label`` — e.g. ``"A"``
        * ``palette`` — override palette for this figure only

        Returns
        -------
        str
            Absolute path of the saved PDF file.
        """
        fig_type = fig_spec.get("type")
        if fig_type is None:
            raise ValueError("Figure spec must include a 'type' key.")
        if fig_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported figure type '{fig_type}'. "
                f"Supported: {sorted(SUPPORTED_TYPES)}"
            )

        data = fig_spec.get("data")
        if data is None:
            raise ValueError("Figure spec must include a 'data' key.")

        output = fig_spec.get("output")
        if output is None:
            raise ValueError("Figure spec must include an 'output' key.")

        # Resolve per-figure palette override
        colors = self._colors
        if "palette" in fig_spec:
            colors = self._resolve_palette(fig_spec["palette"])

        style = fig_spec.get("style", {})
        figsize = tuple(fig_spec.get("figsize", [6, 4]))

        with matplotlib.rc_context(self._rcparams):
            if fig_type == "multi_panel":
                fig = self._draw_multi_panel(data, figsize, style, colors)
            else:
                fig, ax = plt.subplots(figsize=figsize)
                draw_fn = self._get_draw_fn(fig_type)
                draw_fn(ax, data, style, colors)

                # Common decorations
                if fig_spec.get("title"):
                    ax.set_title(fig_spec["title"], pad=8)
                if fig_spec.get("xlabel"):
                    ax.set_xlabel(fig_spec["xlabel"])
                if fig_spec.get("ylabel"):
                    ax.set_ylabel(fig_spec["ylabel"])
                if fig_spec.get("panel_label"):
                    self._add_panel_label(fig, fig_spec["panel_label"])

                fig.tight_layout()

            saved = self._save(fig, output)
            plt.close(fig)

        return saved

    def create_all(self, figure_specs: list[dict]) -> list[str]:
        """Render every spec in *figure_specs*, returning saved paths."""
        paths: list[str] = []
        for idx, spec in enumerate(figure_specs):
            try:
                paths.append(self.create_figure(spec))
            except Exception:
                logger.exception("Failed to create figure %d (%s).", idx, spec.get("type"))
                raise
        return paths

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def _get_draw_fn(self, fig_type: str):
        mapping = {
            "bar": self._draw_bar,
            "barh": self._draw_barh,
            "line": self._draw_line,
            "scatter": self._draw_scatter,
            "heatmap": self._draw_heatmap,
            "pie": self._draw_pie,
            "roc_curve": self._draw_roc_curve,
            "pr_curve": self._draw_pr_curve,
            "confusion_matrix": self._draw_confusion_matrix,
            "tsne": self._draw_tsne,
            "violin": self._draw_violin,
            "box": self._draw_box,
            "network": self._draw_network,
        }
        return mapping[fig_type]

    # ------------------------------------------------------------------
    # Drawing methods
    # ------------------------------------------------------------------
    def _draw_bar(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Vertical bar chart.

        *data* keys: ``labels``, ``values``, and optionally ``errors``, ``group_labels``
        for grouped bars.
        """
        labels = data["labels"]
        values = np.asarray(data["values"])
        errors = data.get("errors")

        if values.ndim == 2:
            # Grouped bar chart
            n_groups, n_bars = values.shape
            group_labels = data.get("group_labels", [f"Group {i}" for i in range(n_bars)])
            x = np.arange(n_groups)
            width = 0.8 / n_bars
            for i in range(n_bars):
                offset = (i - n_bars / 2 + 0.5) * width
                err = np.asarray(errors)[: , i] if errors is not None else None
                ax.bar(
                    x + offset,
                    values[:, i],
                    width,
                    yerr=err,
                    label=group_labels[i],
                    color=colors[i % len(colors)],
                    edgecolor="white",
                    linewidth=0.5,
                    capsize=2,
                    **style,
                )
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend(frameon=False)
        else:
            bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
            ax.bar(
                labels,
                values,
                yerr=errors,
                color=bar_colors,
                edgecolor="white",
                linewidth=0.5,
                capsize=2,
                **style,
            )

    def _draw_barh(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Horizontal bar chart.

        *data* keys: ``labels``, ``values``, optionally ``errors``.
        """
        labels = data["labels"]
        values = np.asarray(data["values"])
        errors = data.get("errors")
        bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

        ax.barh(
            labels,
            values,
            xerr=errors,
            color=bar_colors,
            edgecolor="white",
            linewidth=0.5,
            capsize=2,
            **style,
        )
        ax.invert_yaxis()

    def _draw_line(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Line plot (single or multi-series).

        *data* keys: ``x``, ``y`` (list of lists for multi), ``labels`` (optional).
        """
        x = np.asarray(data["x"])
        y_series = data["y"]
        labels = data.get("labels")

        # Normalise to list-of-series
        if np.ndim(y_series) == 1:
            y_series = [y_series]
            labels = labels or [None]
        elif labels is None:
            labels = [None] * len(y_series)

        marker = style.pop("marker", "o")
        for i, (y, lab) in enumerate(zip(y_series, labels)):
            ax.plot(
                x,
                np.asarray(y),
                marker=marker,
                color=colors[i % len(colors)],
                label=lab,
                **style,
            )
        if any(lab is not None for lab in labels):
            ax.legend(frameon=False)

    def _draw_scatter(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Scatter plot.

        *data* keys: ``x``, ``y``, optionally ``hue`` (int labels),
        ``hue_labels``, ``sizes``.
        """
        x = np.asarray(data["x"])
        y = np.asarray(data["y"])
        hue = data.get("hue")

        if hue is not None:
            hue = np.asarray(hue)
            hue_labels = data.get("hue_labels", {})
            for val in np.unique(hue):
                mask = hue == val
                label = hue_labels.get(str(int(val)), str(val))
                ax.scatter(
                    x[mask],
                    y[mask],
                    c=colors[int(val) % len(colors)],
                    label=label,
                    alpha=style.get("alpha", 0.7),
                    s=style.get("s", 30),
                    edgecolors="white",
                    linewidths=0.3,
                )
            ax.legend(frameon=False)
        else:
            ax.scatter(
                x,
                y,
                c=colors[0],
                alpha=style.get("alpha", 0.7),
                s=style.get("s", 30),
                edgecolors="white",
                linewidths=0.3,
            )

    def _draw_heatmap(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Heatmap via seaborn.

        *data* keys: ``matrix``, optionally ``xlabels``, ``ylabels``.
        """
        matrix = np.asarray(data["matrix"])
        kwargs: dict[str, Any] = {
            "annot": style.get("annot", True),
            "fmt": style.get("fmt", ".2f"),
            "cmap": style.get("cmap", "RdBu_r"),
            "center": style.get("center"),
            "linewidths": style.get("linewidths", 0.5),
            "square": style.get("square", True),
            "cbar_kws": {"shrink": 0.8},
        }

        xlabels = data.get("xlabels")
        ylabels = data.get("ylabels")
        if xlabels is not None:
            kwargs["xticklabels"] = xlabels
        if ylabels is not None:
            kwargs["yticklabels"] = ylabels

        # Heatmap needs all four spines
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)

        sns.heatmap(matrix, ax=ax, **kwargs)

    def _draw_pie(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Pie / donut chart.

        *data* keys: ``labels``, ``values``.
        """
        labels = data["labels"]
        values = np.asarray(data["values"], dtype=float)
        wedge_colors = [colors[i % len(colors)] for i in range(len(labels))]

        wedgeprops = {"edgecolor": "white", "linewidth": 1}
        if style.get("donut"):
            wedgeprops["width"] = style.get("donut_width", 0.4)

        ax.pie(
            values,
            labels=labels,
            colors=wedge_colors,
            autopct=style.get("autopct", "%1.1f%%"),
            startangle=style.get("startangle", 90),
            wedgeprops=wedgeprops,
        )
        ax.set_aspect("equal")
        # Pie charts don't use spines
        for spine in ax.spines.values():
            spine.set_visible(False)

    def _draw_roc_curve(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """ROC curve(s).

        *data* keys: ``curves`` — list of dicts each with ``fpr``, ``tpr``,
        ``auc`` (float), ``label``.
        """
        curves = data.get("curves", [data])
        for i, curve in enumerate(curves):
            fpr = np.asarray(curve["fpr"])
            tpr = np.asarray(curve["tpr"])
            auc_val = curve.get("auc")
            label = curve.get("label", f"Model {i + 1}")
            if auc_val is not None:
                label = f"{label} (AUC = {auc_val:.3f})"
            ax.plot(fpr, tpr, color=colors[i % len(colors)], label=label, **style)

        ax.plot([0, 1], [0, 1], linestyle="--", color="#999999", linewidth=0.8)
        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.02])
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.legend(loc="lower right", frameon=False)

    def _draw_pr_curve(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Precision-Recall curve(s).

        *data* keys: ``curves`` — list of dicts each with ``recall``,
        ``precision``, ``ap`` (average precision), ``label``.
        """
        curves = data.get("curves", [data])
        for i, curve in enumerate(curves):
            recall = np.asarray(curve["recall"])
            precision = np.asarray(curve["precision"])
            ap = curve.get("ap")
            label = curve.get("label", f"Model {i + 1}")
            if ap is not None:
                label = f"{label} (AP = {ap:.3f})"
            ax.plot(recall, precision, color=colors[i % len(colors)], label=label, **style)

        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.05])
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.legend(loc="lower left", frameon=False)

    def _draw_confusion_matrix(
        self, ax: plt.Axes, data: dict, style: dict, colors: list[str]
    ) -> None:
        """Confusion matrix.

        *data* keys: ``matrix``, optionally ``labels``.
        """
        matrix = np.asarray(data["matrix"])
        labels = data.get("labels")

        # Re-enable spines for the matrix
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)

        kwargs: dict[str, Any] = {
            "annot": True,
            "fmt": style.get("fmt", "d"),
            "cmap": style.get("cmap", "Blues"),
            "linewidths": 0.5,
            "square": True,
            "cbar": False,
        }
        if labels is not None:
            kwargs["xticklabels"] = labels
            kwargs["yticklabels"] = labels

        sns.heatmap(matrix, ax=ax, **kwargs)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")

    def _draw_tsne(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """t-SNE / UMAP embedding scatter.

        *data* keys: ``x``, ``y``, ``labels`` (int cluster ids),
        optionally ``label_names``.
        """
        x = np.asarray(data["x"])
        y = np.asarray(data["y"])
        cluster_ids = np.asarray(data["labels"])
        label_names = data.get("label_names", {})
        alpha = style.get("alpha", 0.6)
        s = style.get("s", 15)

        for cid in np.unique(cluster_ids):
            mask = cluster_ids == cid
            name = label_names.get(str(int(cid)), f"Cluster {cid}")
            ax.scatter(
                x[mask],
                y[mask],
                c=colors[int(cid) % len(colors)],
                label=name,
                alpha=alpha,
                s=s,
                edgecolors="none",
            )
        ax.legend(frameon=False, markerscale=1.5)
        ax.set_xticks([])
        ax.set_yticks([])

    def _draw_violin(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Violin plot via seaborn.

        *data* keys: ``groups`` — dict mapping group name to list of values.
        """
        groups = data["groups"]
        names = list(groups.keys())
        values = [np.asarray(groups[n]) for n in names]
        palette = {n: colors[i % len(colors)] for i, n in enumerate(names)}

        import pandas as pd

        rows = []
        for name, vals in zip(names, values):
            for v in vals:
                rows.append({"group": name, "value": float(v)})
        df = pd.DataFrame(rows)

        sns.violinplot(
            data=df,
            x="group",
            y="value",
            hue="group",
            palette=palette,
            inner=style.get("inner", "box"),
            cut=style.get("cut", 0),
            ax=ax,
            legend=False,
        )

    def _draw_box(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Box plot via seaborn.

        *data* keys: ``groups`` — dict mapping group name to list of values.
        """
        groups = data["groups"]
        names = list(groups.keys())
        palette = {n: colors[i % len(colors)] for i, n in enumerate(names)}

        import pandas as pd

        rows = []
        for name in names:
            for v in groups[name]:
                rows.append({"group": name, "value": float(v)})
        df = pd.DataFrame(rows)

        sns.boxplot(
            data=df,
            x="group",
            y="value",
            hue="group",
            palette=palette,
            width=style.get("width", 0.5),
            fliersize=style.get("fliersize", 3),
            ax=ax,
            legend=False,
        )

    def _draw_network(self, ax: plt.Axes, data: dict, style: dict, colors: list[str]) -> None:
        """Simple network / graph visualisation (no networkx dependency).

        *data* keys:
        * ``nodes`` — list of dicts with ``id``, optionally ``x``, ``y``,
          ``group``, ``size``, ``label``.
        * ``edges`` — list of ``[source_id, target_id]`` or dicts with
          ``source``, ``target``, optionally ``weight``.
        """
        nodes = data["nodes"]
        edges = data["edges"]

        # Build position map
        positions: dict[Any, tuple[float, float]] = {}
        node_map: dict[Any, dict] = {}
        for node in nodes:
            nid = node["id"]
            node_map[nid] = node
            if "x" in node and "y" in node:
                positions[nid] = (float(node["x"]), float(node["y"]))

        # Auto-layout if positions missing (circle layout)
        if len(positions) < len(nodes):
            n = len(nodes)
            for i, node in enumerate(nodes):
                nid = node["id"]
                if nid not in positions:
                    angle = 2 * np.pi * i / n
                    positions[nid] = (np.cos(angle), np.sin(angle))

        # Draw edges
        for edge in edges:
            if isinstance(edge, dict):
                src, tgt = edge["source"], edge["target"]
                weight = edge.get("weight", 1.0)
            else:
                src, tgt = edge[0], edge[1]
                weight = 1.0
            if src in positions and tgt in positions:
                x0, y0 = positions[src]
                x1, y1 = positions[tgt]
                ax.plot(
                    [x0, x1],
                    [y0, y1],
                    color="#cccccc",
                    linewidth=0.5 + float(weight) * 0.5,
                    zorder=1,
                )

        # Draw nodes
        for node in nodes:
            nid = node["id"]
            x, y = positions[nid]
            group = node.get("group", 0)
            size = node.get("size", 80)
            color = colors[int(group) % len(colors)]
            ax.scatter(x, y, c=color, s=size, zorder=2, edgecolors="white", linewidths=0.5)
            if node.get("label"):
                ax.annotate(
                    node["label"],
                    (x, y),
                    fontsize=6,
                    ha="center",
                    va="bottom",
                    xytext=(0, 4),
                    textcoords="offset points",
                )

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect("equal")

    # ------------------------------------------------------------------
    # Multi-panel
    # ------------------------------------------------------------------
    def _draw_multi_panel(
        self,
        data: dict,
        figsize: tuple[float, float],
        style: dict,
        colors: list[str],
    ) -> plt.Figure:
        """Multi-panel figure.

        *data* keys:

        * ``panels`` — list of sub-specs (same format as a top-level spec,
          minus ``output``).
        * ``layout`` — optional ``[nrows, ncols]`` (auto-computed if absent).
        * ``title`` — optional super-title.
        """
        panels: list[dict] = data["panels"]
        n = len(panels)
        if "layout" in data:
            nrows, ncols = data["layout"]
        else:
            ncols = min(n, 3)
            nrows = int(np.ceil(n / ncols))

        fig = plt.figure(figsize=figsize)
        gs = gridspec.GridSpec(nrows, ncols, figure=fig)

        for idx, panel in enumerate(panels):
            row, col = divmod(idx, ncols)
            ax = fig.add_subplot(gs[row, col])

            ptype = panel.get("type")
            if ptype is None or ptype not in SUPPORTED_TYPES or ptype == "multi_panel":
                logger.warning("Skipping invalid panel %d (type=%s).", idx, ptype)
                continue

            panel_colors = colors
            if "palette" in panel:
                panel_colors = self._resolve_palette(panel["palette"])

            draw_fn = self._get_draw_fn(ptype)
            pstyle = panel.get("style", {})
            draw_fn(ax, panel["data"], pstyle, panel_colors)

            if panel.get("title"):
                ax.set_title(panel["title"], pad=6)
            if panel.get("xlabel"):
                ax.set_xlabel(panel["xlabel"])
            if panel.get("ylabel"):
                ax.set_ylabel(panel["ylabel"])

            # Panel label (A, B, C ...)
            label = panel.get("panel_label")
            if label is None:
                label = chr(ord("A") + idx)
            self._add_panel_label(fig, label, ax=ax)

        if data.get("title"):
            fig.suptitle(data["title"], fontsize=11, fontweight="bold", y=1.02)

        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _add_panel_label(
        fig: plt.Figure,
        label: str,
        ax: plt.Axes | None = None,
    ) -> None:
        """Place a bold panel label (e.g. 'A') in the top-left corner."""
        if ax is None:
            # Whole-figure label
            fig.text(
                0.02,
                0.98,
                label,
                fontsize=12,
                fontweight="bold",
                va="top",
                ha="left",
                transform=fig.transFigure,
            )
        else:
            ax.text(
                -0.08,
                1.08,
                label,
                fontsize=12,
                fontweight="bold",
                va="top",
                ha="left",
                transform=ax.transAxes,
            )

    @staticmethod
    def _save(fig: plt.Figure, output: str) -> str:
        """Save *fig* as both PDF and PNG, returning the PDF path."""
        out = Path(output)
        # Strip any extension the caller may have added
        stem = out.with_suffix("")
        parent = stem.parent
        parent.mkdir(parents=True, exist_ok=True)

        pdf_path = stem.with_suffix(".pdf")
        png_path = stem.with_suffix(".png")

        fig.savefig(str(pdf_path), format="pdf")
        fig.savefig(str(png_path), format="png", dpi=300)

        logger.info("Saved %s and %s", pdf_path, png_path)
        return str(pdf_path.resolve())
