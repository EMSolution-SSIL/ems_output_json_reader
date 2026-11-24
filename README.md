# EMSolution output.json reader

`emso-post` reads EMSolution `output.json` post-processing results, exports selected time series to Excel-friendly CSV, and plots them in a standalone window. It does not require EMSolution itself to be installed. Convergence and mesh summary files are planned for a later release.

[日本語 README](README_ja.md) · [Roadmap](ROADMAP.md)

## Related repositories

| Repository | Purpose | License |
| --- | --- | --- |
| [EMSolution input.json checker](https://github.com/EMSolution-SSIL/ems_input_json_reader) | Statically checks input settings before running EMSolution (`emso-input`). | PolyForm Perimeter 1.0.1 (source available) |
| [EMSolution output.json reader](https://github.com/EMSolution-SSIL/ems_output_json_reader) | Exports and plots post-processing results (`emso-post`). | MIT |

These are independent Python packages; install the one needed for each task.

## Install

Python 3.10 or newer is required. Install from a clone for CSV export:

```sh
python -m pip install -e .
```

Install the optional plotting dependencies for the standalone window:

```sh
python -m pip install -e ".[plot]"
```

You can also download the universal `.whl` file from [GitHub Releases](https://github.com/EMSolution-SSIL/ems_output_json_reader/releases) and install it with `python -m pip install path/to/emso_post-*.whl`. PyPI publication is not required.

## Command line

```sh
emso-post run path/to/output.json --config selection.yaml --out results
emso-post run path/to/output.json --out results
emso-post export path/to/output.json --out results
emso-post plot path/to/output.json
```

`run` exports CSV and opens the plot window. `export` is suitable for batch use; `plot` only opens the plot window. You may pass an `output.json` file or its containing directory. Without `--config`, all available numeric time series are exported. Without `--out`, CSV files go to a `post_csv` directory beside the input. Existing files are protected; pass `--overwrite` to replace them.

CSV files are organized by post-data group, for example `forceNodal_forceNodalData.csv`. The columns include step, time, available position/angle axes, and series names with IDs and units. B-integration point coordinates are exported separately as `binteg_points.csv`. Files use UTF-8 with a BOM for convenient opening in Excel.

## Select data with YAML

```yaml
exports:
  - post: forceNodal
    group: forceNodalData
    ids: [rotor, 10]
    fields: [forceMZ, forceX]
  - post: network
    group: networkData
    ids: [1, 2, 3]
    fields: [current, voltage, flux]
```

`post` is required. Omit `group`, `ids`, or `fields` to select everything in that scope. Use the same ID type as the JSON file. Composite IDs use a mapping, for example `ids: [{seriesNum: 1, divisionNum: 2}]`. Unknown names and missing ID/field combinations produce an error. See [examples/selection.yaml](examples/selection.yaml).

The plot window always reads the full `output.json`; a YAML selection only limits CSV export. In the window, choose a post-data type, group, one or more IDs and fields, and an x-axis. A short value preview appears before plotting. Series with different units are placed on separate vertical axes. Single-point results are shown with markers.

Plotting uses Matplotlib and Tkinter. Tkinter is normally available with standard Windows Python installations; on other systems it may need a separate OS package.

## Python API

```python
from emso_post import load_output, load_selection, select_series, export_csv

output = load_output("path/to/output.json")
for series in output.series:
    print(series.post, series.group, series.id_label, series.field, series.unit)

selection = load_selection("selection.yaml")
chosen = select_series(output, selection)
paths = export_csv(output, "results", selection)
```

`output.raw` retains the complete parsed JSON and `output.axes` contains the available x-axes. For ordinary groups, the series catalog refers to the original numeric arrays rather than duplicating them.

## Supported data and testing

The reader recognizes the 14 post-data types written by the current EMSolution `src/post/post_files/EMSOJson.cpp`, including the producer's `electriccEnergy` spelling and `demagRatio`. It also recognizes optional `network.convertedData`, `forceNodal.forceNodalExtendData`, and `heat.sourceHeatData` groups. Unknown post-data types, unsupported array groups, and inconsistent time-series lengths fail explicitly instead of being silently dropped.

The validation corpus in `../reader_json_files/results` contains 240 outputs. All 240 load successfully: 221 have every value indexed as a time series, 18 have keys without produced values, and one has valid MESH spatial values. The JSON corpus report identifies the 2026.09.2 ComplexPermeability bug and the MESH geometry-point output. These values are listed in `output.unindexed`, while `output.raw` retains the original JSON. Repeated IDs get a `recordNo` identity, and YAML may select all such records by their original ID. See [the validation report](VALIDATION_REPORT.md). No validation model or full solver result is included in this repository.

Run the tests with:

```sh
python -m unittest discover -s tests -v
python tests/run_corpus.py --root ../reader_json_files --report build/corpus_report.json
```

The corpus script writes a per-file JSON report. Exit code 0 means every file was read and any unindexed values were classified as absent results or valid MESH spatial data; 1 means a file could not be read or parsed; 2 means an unclassified unindexed value remains. Use `--allow-incomplete` when such values are acceptable. The corpus itself is kept outside the package.

The old motor-specific experimental scripts are intentionally outside this distributable package. See the [roadmap](ROADMAP.md) for convergence and mesh data support.

## License

MIT. See [LICENSE](LICENSE).
