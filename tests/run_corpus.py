"""Run the output reader against an external EMSolution JSON corpus.

Usage: python tests/run_corpus.py --root C:\\EMSolution\\build\\reader_json_files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from emso_post import load_output  # noqa: E402


def classify_unindexed(relative: str, unindexed: tuple[str, ...]) -> tuple[str, list[str]]:
    """Separate absent values and MESH spatial output from conversion failures."""
    if not unindexed:
        return "full", []
    empty = all(item.endswith((": null", ": empty array", ": no post results")) for item in unindexed)
    spatial = all("mesh spatial values (" in item for item in unindexed)
    if empty:
        if relative.startswith("030_AC/010_ComplexPermeability/"):
            return "empty_result", [
                "2026.09.2 ComplexPermeability solver bug: result data were absent; corrected after this validation run."
            ]
        return "empty_result", ["The keys are present, but no values were produced for these items."]
    if spatial:
        return "spatial", [
            "MESH coilForce values correspond to geometry data points, not to time steps; raw arrays are retained."
        ]
    return "incomplete", ["Some values could not be classified as absent or MESH spatial data."]


def scan(root: Path) -> dict:
    folder = root / "results"
    if not folder.is_dir():
        raise FileNotFoundError(f"Results folder does not exist: {folder}")
    files = sorted(folder.rglob("*.json"))
    cases = []
    counts = {"full": 0, "empty_result": 0, "spatial": 0, "incomplete": 0, "error": 0}
    total_series = 0
    for path in files:
        relative = path.relative_to(folder).as_posix()
        try:
            output = load_output(path)
        except Exception as exc:
            counts["error"] += 1
            cases.append({"file": relative, "status": "error", "message": str(exc)})
            continue
        total_series += len(output.series)
        status, notes = classify_unindexed(relative, output.unindexed)
        counts[status] += 1
        cases.append({
            "file": relative,
            "status": status,
            "steps": output.num_steps,
            "series": len(output.series),
            "unindexed": list(output.unindexed),
            "notes": notes,
        })
    return {"root": str(root), "files": len(files), "counts": counts,
            "total_series": total_series, "cases": cases}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check every output JSON in an EMSolution result corpus")
    parser.add_argument("--root", type=Path, default=PROJECT.parent / "reader_json_files")
    parser.add_argument("--report", type=Path, help="Write the complete UTF-8 JSON report here")
    parser.add_argument("--allow-incomplete", action="store_true", help="Return 0 when only unindexed data remains")
    args = parser.parse_args(argv)
    try:
        report = scan(args.root.resolve())
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        parser.exit(3, f"{exc}\n")
    print(f"outputs={report['files']} full={report['counts']['full']} "
          f"empty_result={report['counts']['empty_result']} spatial={report['counts']['spatial']} "
          f"incomplete={report['counts']['incomplete']} error={report['counts']['error']} "
          f"series={report['total_series']}")
    for case in report["cases"]:
        if case["status"] == "error":
            print(f"ERROR {case['file']}: {case['message']}")
    if args.report:
        print(f"report={args.report}")
    if report["counts"]["error"]:
        return 1
    if report["counts"]["incomplete"] and not args.allow_incomplete:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
