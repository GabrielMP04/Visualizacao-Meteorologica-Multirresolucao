"""Graficos da comparacao experimental sem LOD e com LOD."""

from __future__ import annotations

import csv
from pathlib import Path


def create_comparison_chart(
    summary_csv: str | Path, output_path: str | Path | None = None
) -> Path:
    """Cria um PNG com FPS, tempo de quadro e triangulos medios."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    source = Path(summary_csv)
    with source.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("o resumo do benchmark esta vazio")

    preferred_order = {"sem_lod": 0, "com_lod": 1}
    rows.sort(key=lambda row: preferred_order.get(row["mode"], 99))
    labels = ["Sem LOD" if row["mode"] == "sem_lod" else "Com LOD" for row in rows]
    colors = ["#d95f4c", "#2d8f72"][: len(rows)]
    series = (
        ("mean_fps", "FPS medio", "quadros/s"),
        ("mean_frame_time_ms", "Tempo medio por quadro", "ms"),
        ("mean_triangles", "Triangulos medios", "triangulos"),
    )

    figure, axes = plt.subplots(1, 3, figsize=(12.0, 4.2), constrained_layout=True)
    for axis, (field, title, unit) in zip(axes, series, strict=True):
        values = [float(row[field]) for row in rows]
        bars = axis.bar(labels, values, color=colors, width=0.62)
        axis.set_title(title, fontsize=11, weight="bold")
        axis.set_ylabel(unit)
        axis.grid(axis="y", alpha=0.24)
        axis.set_axisbelow(True)
        maximum = max(values) if values else 1.0
        axis.set_ylim(0.0, maximum * 1.18 if maximum > 0 else 1.0)
        for bar, value in zip(bars, values, strict=True):
            label = f"{value:,.1f}" if value < 10000 else f"{value:,.0f}"
            axis.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + maximum * 0.025,
                label,
                ha="center",
                va="bottom",
                fontsize=9,
            )

    figure.suptitle("Comparacao experimental: terreno uniforme x LOD", fontsize=14)
    destination = (
        Path(output_path)
        if output_path is not None
        else source.with_name(source.stem.replace("_resumo", "_grafico") + ".png")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180, facecolor="white")
    plt.close(figure)
    return destination
