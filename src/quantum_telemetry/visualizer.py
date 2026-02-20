"""Visualization helpers for IBM Quantum measurement results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt  # noqa: E402


def plot_measurement_counts(
    counts: dict[str, Any],
    *,
    title: str = "Measurement Counts",
    output_path: str | Path | None = None,
) -> None:
    """Plot a bar chart of measurement bitstring counts.

    Parameters
    ----------
    counts : dict[str, Any]
        Mapping from bitstring label to count (or probability).
    title : str
        Chart title.
    output_path : str | Path | None
        If provided, save the figure to this path instead of displaying it.
    """
    sorted_items = sorted(counts.items(), key=lambda item: str(item[0]))
    labels = [str(k) for k in [item[0] for item in sorted_items]]
    values = [float(v) for v in [item[1] for item in sorted_items]]

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.6), 4))
    ax.bar(labels, values, color="#1f77b4")
    ax.set_xlabel("Bitstring")
    ax.set_ylabel("Counts")
    ax.set_title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    if output_path is not None:
        fig.savefig(str(output_path))
    plt.close(fig)
