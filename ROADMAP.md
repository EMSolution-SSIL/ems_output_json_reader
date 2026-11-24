# Roadmap

The initial `output.json` reader, CSV exporter, and standalone plotter were implemented in version 0.1.0. The version 0.1.1 validation corpus covers 240 solver outputs: all load, 221 are fully indexed as time series, 18 have no produced values for some keys, and one has valid MESH spatial values. No unclassified values remain. Synthetic tests derived from the producer cover all 14 post-data types.

Future work:

- Read and visualize `convergence_history.json` for ICCG and Newton–Raphson convergence.
- Summarize `mesh_info.json` counts and boundary/region information.
- Rebuild motor-specific dq and torque calculations on top of the shared reader.

The local working plan, including machine-specific paths, is intentionally excluded from this public repository.
