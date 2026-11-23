# Contributing

Issues and pull requests are welcome. Please describe the EMSolution version, the post-data key, and the expected behavior when reporting a format problem.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Add a small synthetic fixture based on the JSON producer's field layout when adding a post-data type. Include tests for IDs, units, array lengths, YAML selection, and CSV values. The CI checkout contains only synthetic data; the local EMSolution result files are deliberately excluded.

Please do not attach customer models, proprietary EMSolution source code, or unredacted simulation results to issues or pull requests. Reduce a reproducer to a minimal synthetic JSON example.
