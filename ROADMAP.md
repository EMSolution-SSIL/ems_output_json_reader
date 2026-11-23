# Roadmap

The initial `output.json` reader, CSV exporter, and standalone plotter are implemented in version 0.1.0. `network` and `forceNodal` are also checked against local solver output. The other post-data groups have synthetic tests derived from the current EMSolution JSON producer; real output samples will be checked as they become available.

Future work:

- Read and visualize `convergence_history.json` for ICCG and Newton–Raphson convergence.
- Summarize `mesh_info.json` counts and boundary/region information.
- Rebuild motor-specific dq and torque calculations on top of the shared reader.

The local working plan, including machine-specific paths, is intentionally excluded from this public repository.
