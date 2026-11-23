"""Validate YAML selections against series actually present in output.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import OutputData, PostSeries


class SelectionError(ValueError):
    """A YAML selection is malformed or refers to absent data."""


def load_selection(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SelectionError("YAML を使うには PyYAML をインストールしてください") from exc
    path = Path(path)
    try:
        selection = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SelectionError(f"{path}: YAML を読み込めません: {exc}") from exc
    if not isinstance(selection, dict) or set(selection) != {"exports"}:
        raise SelectionError("YAML の最上位には exports だけを指定してください")
    if not isinstance(selection["exports"], list) or not selection["exports"]:
        raise SelectionError("exports には 1 件以上の選択を指定してください")
    return selection


def _check_list(entry: dict[str, Any], name: str, index: int) -> list[Any] | None:
    value = entry.get(name)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise SelectionError(f"exports[{index}].{name}: 1 件以上の配列が必要です")
    return value


def _id_matches(series: PostSeries, selector: Any) -> bool:
    if isinstance(selector, dict):
        if not selector or any(not isinstance(key, str) for key in selector):
            return False
        identity = dict(series.identity)
        return set(selector) == set(identity) and all(
            type(selector[key]) is type(identity[key]) and selector[key] == identity[key]
            for key in selector
        )
    if len(series.identity) != 1:
        return False
    value = series.identity[0][1]
    return type(selector) is type(value) and selector == value


def select_series(output: OutputData, selection: dict[str, Any] | None = None) -> list[PostSeries]:
    """Return all series or the validated YAML subset, preserving JSON order."""
    if selection is None:
        return list(output.series)
    if not isinstance(selection, dict) or set(selection) != {"exports"}:
        raise SelectionError("選択には exports だけを指定してください")
    entries = selection["exports"]
    if not isinstance(entries, list) or not entries:
        raise SelectionError("exports には 1 件以上の選択を指定してください")
    selected: set[int] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not set(entry) <= {"post", "group", "ids", "fields"}:
            raise SelectionError(f"exports[{index}]: post, group, ids, fields だけを指定してください")
        post = entry.get("post")
        group = entry.get("group")
        if not isinstance(post, str) or not post:
            raise SelectionError(f"exports[{index}].post: ポストデータ名が必要です")
        if group is not None and (not isinstance(group, str) or not group):
            raise SelectionError(f"exports[{index}].group: データ群名は文字列にしてください")
        candidates = [s for s in output.series if s.post == post and (group is None or s.group == group)]
        if not candidates:
            raise SelectionError(f"exports[{index}]: {post}/{group or '*'} に時系列がありません")
        ids = _check_list(entry, "ids", index)
        fields = _check_list(entry, "fields", index)
        if fields is not None and any(not isinstance(field, str) for field in fields):
            raise SelectionError(f"exports[{index}].fields: 項目名は文字列にしてください")
        if ids is not None:
            for selector in ids:
                if not any(_id_matches(s, selector) for s in candidates):
                    raise SelectionError(f"exports[{index}].ids: ID {selector!r} がありません")
        if fields is not None:
            for field in fields:
                if not any(s.field == field for s in candidates):
                    raise SelectionError(f"exports[{index}].fields: 項目 {field!r} がありません")
        if ids is not None and fields is not None:
            for selector in ids:
                for field in fields:
                    if not any(_id_matches(s, selector) and s.field == field for s in candidates):
                        raise SelectionError(
                            f"exports[{index}]: ID {selector!r} に項目 {field!r} がありません"
                        )
        matches = [s for s in candidates
                   if (ids is None or any(_id_matches(s, selector) for selector in ids))
                   and (fields is None or s.field in fields)]
        if not matches:
            raise SelectionError(f"exports[{index}]: 条件に一致する時系列がありません")
        selected.update(id(s) for s in matches)
    return [s for s in output.series if id(s) in selected]
