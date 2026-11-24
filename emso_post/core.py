"""Discover time series in EMSolution's output.json without discarding raw data.

The field names and group layouts follow src/post/post_files/EMSOJson.cpp in
EMSolBuild_VS2022. Some files also contain values added by downstream tools.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


class SeriesError(ValueError):
    """An output file cannot be represented faithfully as time series."""


Number = int | float | None
Identifier = int | str


@dataclass(frozen=True)
class GroupSpec:
    ids: tuple[str, ...]
    unit_key: str


# Keep the producer's spelling of electriccEnergy. A group can have several
# ID fields when one number alone does not identify an entity.
GROUPS: dict[str, dict[str, GroupSpec]] = {
    "electrostatic": {"sourceData": GroupSpec(("sourceID",), "electrostaticUnit")},
    "circuit": {
        "sourceData": GroupSpec(("serialNum",), "circuitUnit"),
        "powerSourceData": GroupSpec(("serialNum",), "circuitUnit"),
    },
    "network": {
        "networkData": GroupSpec(("elementNum",), "networkUnit"),
        "convertedData": GroupSpec(("elementNum",), "networkUnit"),
    },
    "binteg": {"magneticDensity": GroupSpec(("pointNum",), "magneticDensityUnit")},
    "magFlux": {"fluxData": GroupSpec(("loopNum",), "fluxUnit")},
    "curFlux": {"currentData": GroupSpec(("surfaceNum",), "currentUnit")},
    "heat": {
        "heatData": GroupSpec(("propertyNum",), "heatUnit"),
        "sourceHeatData": GroupSpec(("sourceNum",), "heatUnit"),
    },
    "forceJB": {"forceJBData": GroupSpec(("propertyNum",), "forceUnit")},
    "forceNodal": {
        "forceNodalData": GroupSpec(("propertyNum",), "forceUnit"),
        "forceNodalExtendData": GroupSpec(("propertyNum",), "forceUnit"),
    },
    "magneticEnergy": {"magneticEnergyData": GroupSpec(("propertyNum",), "energyUnit")},
    "electriccEnergy": {"electricEnergyData": GroupSpec(("propertyNum",), "energyUnit")},
    "ironLoss": {"ironLossData": GroupSpec(("propertyNum",), "lossUnit")},
    "coilForce": {"coilForceData": GroupSpec(("seriesNum", "divisionNum"), "forceUnit")},
    "demagRatio": {"demagRatioData": GroupSpec(("propertyNum",), "demagRatioUnit")},
}


@dataclass(frozen=True)
class Axis:
    name: str
    unit: str
    values: Sequence[Number]

    @property
    def label(self) -> str:
        return f"{self.name} [{self.unit}]" if self.unit else self.name


@dataclass(frozen=True)
class PostSeries:
    post: str
    group: str
    identity: tuple[tuple[str, Identifier], ...]
    field: str
    unit: str
    values: Sequence[Number]

    @property
    def id_label(self) -> str:
        return ", ".join(f"{key}={value}" for key, value in self.identity)

    @property
    def label(self) -> str:
        unit = f" [{self.unit}]" if self.unit else ""
        return f"{self.id_label} {self.field}{unit}"


@dataclass
class OutputData:
    path: Path
    raw: dict[str, Any]
    axes: dict[str, Axis]
    series: tuple[PostSeries, ...]
    unindexed: tuple[str, ...] = ()

    @property
    def num_steps(self) -> int:
        return len(self.axes["stepNo"].values)

    def series_for(self, post: str, group: str | None = None) -> list[PostSeries]:
        return [s for s in self.series if s.post == post and (group is None or s.group == group)]


def _is_number(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def _numbers(value: Any, context: str, expected: int | None = None) -> Sequence[Number]:
    if not isinstance(value, list) or any(not _is_number(v) for v in value):
        raise SeriesError(f"{context}: 数値または null の配列が必要です")
    if expected is not None and len(value) != expected:
        raise SeriesError(f"{context}: {expected} 個が必要ですが {len(value)} 個です")
    return value


def _unit(raw_unit: Any, index: int = 0) -> str:
    if isinstance(raw_unit, str):
        return raw_unit if index == 0 else ""
    if isinstance(raw_unit, list) and index < len(raw_unit):
        return str(raw_unit[index])
    return ""


def _field_unit(post: str, group: str, field: str, data: dict[str, Any], spec: GroupSpec) -> str:
    units = data.get(spec.unit_key)
    if post == "electrostatic":
        return _unit(units, 0 if field == "potential" else 1)
    if post in ("circuit", "network"):
        if post == "circuit":
            units = data.get("circuitUnit", data.get("sourceUnit"))
        name = field.rsplit("-", 1)[-1]
        return _unit(units, {"current": 0, "voltage": 1, "flux": 2}.get(name, 99))
    if post in ("forceJB", "forceNodal"):
        return _unit(units, 1 if field.startswith("forceM") else 0)
    if post == "magFlux":
        return _unit(units, 1 if field == "absB" else 0)
    return _unit(units)


def _axes(time_step: Any) -> dict[str, Axis]:
    if not isinstance(time_step, dict):
        raise SeriesError("timeStep: オブジェクトが必要です")
    if "stepNo" not in time_step and "frequency" in time_step:
        frequency = time_step["frequency"]
        if frequency is None or not _is_number(frequency) or time_step.get("numSteps") != 1:
            raise SeriesError("timeStep.frequency: AC output requires one numeric frequency")
        return {
            "stepNo": Axis("stepNo", "", (1,)),
            "frequency": Axis("frequency", str(time_step.get("frequencyUnit", "Hz")), (frequency,)),
        }
    steps = _numbers(time_step.get("stepNo"), "timeStep.stepNo")
    if not steps:
        raise SeriesError("timeStep.stepNo: 1 件以上必要です")
    count = len(steps)
    declared = time_step.get("numSteps")
    if declared is not None and declared != count:
        raise SeriesError(f"timeStep.numSteps={declared} と stepNo の長さ {count} が異なります")
    time = _numbers(time_step.get("time"), "timeStep.time", count)
    axes = {
        "stepNo": Axis("stepNo", "", steps),
        "time": Axis("time", str(time_step.get("timeUnit", "s")), time),
    }
    for name, value in time_step.items():
        if name in ("numSteps", "stepNo", "time", "position") or not isinstance(value, list):
            continue
        if len(value) == count and all(_is_number(v) for v in value):
            unit = time_step.get("angleUnit", "") if "angle" in name.lower() else ""
            axes[name] = Axis(name, str(unit), value)
    position = time_step.get("position")
    if position is not None:
        tracks = position if isinstance(position, list) and position and isinstance(position[0], list) else [position]
        position_unit = str(time_step.get("positionUnit", ""))
        track_units = [part.strip() for part in position_unit.split(",")]
        for i, track in enumerate(tracks, 1):
            axes[f"position[{i}]"] = Axis(
                f"position[{i}]", track_units[i - 1] if len(track_units) == len(tracks) else position_unit,
                _numbers(track, f"timeStep.position[{i}]", count),
            )
    return axes


def _identity(item: dict[str, Any], keys: tuple[str, ...], context: str) -> tuple[tuple[str, Identifier], ...]:
    result = []
    for key in keys:
        value = item.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise SeriesError(f"{context}.{key}: 整数または文字列の ID が必要です")
        result.append((key, value))
    return tuple(result)


def _regular_series(
    post: str, group: str, rows: Any, data: dict[str, Any], spec: GroupSpec, count: int,
    unindexed: list[str],
) -> list[PostSeries]:
    if not isinstance(rows, list):
        raise SeriesError(f"postData.{post}.{group}: 配列が必要です")
    output: list[PostSeries] = []
    seen: set[tuple[tuple[tuple[str, Identifier], ...], str]] = set()
    base_ids: list[tuple[tuple[str, Identifier], ...]] = []
    for row_no, item in enumerate(rows, 1):
        context = f"postData.{post}.{group}[{row_no}]"
        if not isinstance(item, dict):
            raise SeriesError(f"{context}: expected an object")
        base_ids.append(_identity(item, spec.ids, context))
    base_counts = Counter(base_ids)
    labeled_ids = []
    for item, base in zip(rows, base_ids):
        identity = base
        if base_counts[base] > 1 and isinstance(item.get("coilType"), str):
            identity += (("coilType", item["coilType"]),)
        labeled_ids.append(identity)
    labeled_counts = Counter(labeled_ids)
    for row_no, item in enumerate(rows, 1):
        context = f"postData.{post}.{group}[{row_no}]"
        identity = labeled_ids[row_no - 1]
        if labeled_counts[identity] > 1:
            identity += (("recordNo", row_no),)
        for field, values in item.items():
            if field in spec.ids or not isinstance(values, list):
                continue
            if post == "ironLoss" and data.get("type") == "minMax" and count == 1 and len(values) == 2:
                pair = _numbers(values, f"{context}.{field}", 2)
                for suffix, value in zip(("min", "max"), pair):
                    named_field = f"{field}.{suffix}"
                    output.append(PostSeries(post, group, identity, named_field,
                                             _field_unit(post, group, field, data, spec), (value,)))
                continue
            if not values:
                unindexed.append(f"{context}.{field}: empty array")
                continue
            if post == "coilForce" and item.get("coilType") == "MESH" and len(values) != count:
                _numbers(values, f"{context}.{field}")
                unindexed.append(f"{context}.{field}: mesh spatial values ({len(values)} points)")
                continue
            numbers = _numbers(values, f"{context}.{field}", count)
            key = (identity, field)
            if key in seen:
                raise SeriesError(f"{context}.{field}: 同じ ID と項目が重複しています")
            seen.add(key)
            output.append(PostSeries(post, group, identity, field, _field_unit(post, group, field, data, spec), numbers))
    return output


def _binteg_series(data: dict[str, Any], steps: Sequence[Number]) -> list[PostSeries]:
    count = len(steps)
    rows = data.get("magneticDensity", [])
    if not isinstance(rows, list) or len(rows) != count or any(not isinstance(row, dict) for row in rows):
        raise SeriesError("postData.binteg.magneticDensity: ステップ数と同じ長さの配列が必要です")
    points = data.get("points", {})
    if not isinstance(points, dict):
        raise SeriesError("postData.binteg.points: オブジェクトが必要です")
    first = rows[0]
    fields = [key for key, value in first.items() if key != "stepNo" and isinstance(value, list)]
    npoints = len(first[fields[0]]) if fields else 0
    ids = points.get("pointNum", list(range(1, npoints + 1)))
    if not isinstance(ids, list) or len(ids) != npoints:
        raise SeriesError("postData.binteg.points.pointNum: 計算点数が一致しません")
    if len(set(ids)) != len(ids):
        raise SeriesError("postData.binteg.points.pointNum: ID が重複しています")
    for row_no, row in enumerate(rows, 1):
        if row.get("stepNo") != steps[row_no - 1]:
            raise SeriesError(f"postData.binteg.magneticDensity[{row_no}].stepNo: timeStep と一致しません")
        if {key for key, value in row.items() if key != "stepNo" and isinstance(value, list)} != set(fields):
            raise SeriesError(f"postData.binteg.magneticDensity[{row_no}]: 項目が他のステップと異なります")
        for field in fields:
            _numbers(row.get(field), f"postData.binteg.magneticDensity[{row_no}].{field}", npoints)
    for name in ("x", "y", "z"):
        if name in points:
            _numbers(points[name], f"postData.binteg.points.{name}", npoints)
    result = []
    spec = GROUPS["binteg"]["magneticDensity"]
    for index, point_id in enumerate(ids):
        identity = _identity({"pointNum": point_id}, ("pointNum",), "postData.binteg.points")
        for field in fields:
            values = tuple(row[field][index] for row in rows)
            result.append(PostSeries("binteg", "magneticDensity", identity, field,
                                     _field_unit("binteg", "magneticDensity", field, data, spec), values))
    return result


def load_output(path: str | Path) -> OutputData:
    """Load output.json and index all producer-defined numeric time series.

    Unknown post types or array groups raise an error so all-data export cannot
    appear successful after silently omitting new solver output.
    """
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path / "output.json"
    try:
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except UnicodeDecodeError:
            raw = json.loads(path.read_text(encoding="cp932"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeriesError(f"{path}: JSON を読み込めません: {exc}") from exc
    if not isinstance(raw, dict) or "postData" not in raw or (raw["postData"] is not None and not isinstance(raw["postData"], dict)):
        raise SeriesError(f"{path}: output.json の postData オブジェクトがありません")
    axes = _axes(raw.get("timeStep"))
    count = len(axes["stepNo"].values)
    series: list[PostSeries] = []
    unindexed: list[str] = []
    if raw.get("postData") is None:
        unindexed.append("postData: no post results")
    for post, data in (raw.get("postData") or {}).items():
        if post not in GROUPS:
            raise SeriesError(f"postData.{post}: 未対応のポストデータです")
        if not isinstance(data, dict):
            raise SeriesError(f"postData.{post}: オブジェクトが必要です")
        for group, spec in GROUPS[post].items():
            if group not in data:
                continue
            if data[group] is None:
                unindexed.append(f"postData.{post}.{group}: null")
                continue
            if post == "binteg" and group == "magneticDensity":
                series.extend(_binteg_series(data, axes["stepNo"].values))
            else:
                series.extend(_regular_series(post, group, data[group], data, spec, count, unindexed))
        unknown_groups = [name for name, value in data.items()
                          if isinstance(value, list) and value and isinstance(value[0], dict)
                          and name not in GROUPS[post]]
        if unknown_groups:
            raise SeriesError(f"postData.{post}: 未対応のデータ群: {', '.join(unknown_groups)}")
    return OutputData(path, raw, axes, tuple(series), tuple(unindexed))
