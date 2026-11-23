"""Excel-friendly CSV export of selected EMSolution time series."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .core import OutputData, PostSeries, SeriesError
from .selection import select_series


def _points_table(output: OutputData) -> tuple[list[str], list[list[Any]]] | None:
    binteg = output.raw["postData"].get("binteg")
    if not isinstance(binteg, dict) or not isinstance(binteg.get("points"), dict):
        return None
    points = binteg["points"]
    ids = points.get("pointNum", [])
    if not ids:
        return None
    unit = binteg.get("coordinateUnit", "")
    columns = [name for name in ("x", "y", "z") if name in points]
    headers = ["pointNum"] + [f"{name} [{unit}]" if unit else name for name in columns]
    return headers, [[point_id] + [points[name][i] for name in columns] for i, point_id in enumerate(ids)]


def export_csv(
    output: OutputData,
    destination: str | Path,
    selection: dict[str, Any] | None = None,
    *,
    overwrite: bool = False,
) -> list[Path]:
    """Write one wide CSV per post-data group, plus binteg point coordinates.

    Existing files are protected unless overwrite=True. All target paths are
    checked before writing, avoiding a partial export on a name collision.
    """
    chosen = select_series(output, selection)
    grouped: dict[tuple[str, str], list[PostSeries]] = defaultdict(list)
    for series in chosen:
        grouped[(series.post, series.group)].append(series)
    destination = Path(destination).expanduser().resolve()
    files: dict[Path, tuple[list[str], Iterable[list[Any]]]] = {}
    axes = list(output.axes.values())
    for (post, group), items in grouped.items():
        path = destination / f"{post}_{group}.csv"
        headers = [axis.label for axis in axes] + [series.label for series in items]
        rows = (
            [axis.values[index] for axis in axes] + [series.values[index] for series in items]
            for index in range(output.num_steps)
        )
        files[path] = (headers, rows)
    if ("binteg", "magneticDensity") in grouped:
        table = _points_table(output)
        if table is not None:
            files[destination / "binteg_points.csv"] = table
    if not files:
        raise SeriesError(f"{output.path}: 出力可能な時系列がありません")
    if destination.exists() and not destination.is_dir():
        raise SeriesError(f"{destination}: 出力先がディレクトリではありません")
    if not overwrite:
        existing = [str(path) for path in files if path.exists()]
        if existing:
            raise SeriesError("既存の CSV があります。--overwrite を指定してください: " + ", ".join(existing))
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SeriesError(f"{destination}: 出力先を作成できません: {exc}") from exc
    for path, (headers, rows) in files.items():
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerows(rows)
        except OSError as exc:
            raise SeriesError(f"{path}: CSV を書き込めません: {exc}") from exc
    return list(files)
