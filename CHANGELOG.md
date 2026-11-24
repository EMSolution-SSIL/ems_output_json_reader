# Changelog

## 0.1.1 — Unreleased

- Check 240 solver outputs with a repeatable corpus script and per-file JSON report.
- Read AC frequency axes, null result groups, repeated IDs, and min/max iron loss.
- Record empty or spatial arrays as unindexed while retaining their original JSON values.
- Classify absent results and MESH geometry-point arrays as expected corpus outcomes.

## 0.1.0 — 2026-11-23

- Read the post-data groups emitted by the current EMSolution `output.json` producer.
- Select time series with YAML and export Excel-friendly CSV files.
- Browse IDs and fields in a standalone 2D plotting window.
- Provide a Python API, CLI, synthetic tests, and a universal wheel build.
