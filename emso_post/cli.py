"""Command-line interface for CSV export and the independent plot window."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import SeriesError, load_output
from .export import export_csv
from .selection import SelectionError, load_selection


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="emso-post", description="EMSolution output.json の CSV 出力とグラフ表示")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "export", "plot"):
        command = commands.add_parser(name, help={
            "run": "CSV を出力してグラフ画面を開く",
            "export": "CSV のみ出力する",
            "plot": "グラフ画面のみ開く",
        }[name])
        command.add_argument("input", type=Path, help="output.json、またはその格納ディレクトリ")
        if name != "plot":
            command.add_argument("--config", type=Path, help="CSV の対象を選ぶ YAML。省略時は全件")
            command.add_argument("--out", type=Path, help="CSV 出力先。省略時は output.json と同じ場所の post_csv")
            command.add_argument("--overwrite", action="store_true", help="既存の CSV を上書きする")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = load_output(args.input)
        if args.command != "plot":
            selection = load_selection(args.config) if args.config else None
            destination = args.out or output.path.parent / "post_csv"
            paths = export_csv(output, destination, selection, overwrite=args.overwrite)
            for path in paths:
                print(path)
        if args.command != "export":
            from .gui import launch_plot

            launch_plot(output)
    except (SeriesError, SelectionError, ImportError, RuntimeError) as exc:
        print(f"emso-post: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
