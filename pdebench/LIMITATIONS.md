# PDEBench — LIMITATIONS

- PyTorch PINN comparison: IMPLEMENTED 2026-10-08 (history: skipped earlier as
  torch-unavailable, then recorded not-implemented; now built and evaluated on
  torch 2.14.1 CPU). Single smooth test problem; no generality claim about
  PINNs vs grids. Any PINN claim beyond results/pinn.json would be invented —
  none is made.
  Any PINN claim would be invented — none is made.
- Solvers are educational baselines (explicit FTCS, Jacobi); no implicit/multigrid,
  no production CFD, no quantum-advantage claims.
- Jacobi iteration counts grow ~4x per grid refinement (expected); not a
  performance benchmark against other methods.
- Results are local-machine measurements (macOS arm64, numpy 2.2.6), not
  cross-platform guarantees.
- Does not satisfy a PDE-degree or numerical-analysis qualification requirement;
  supports role 36 only as a documented computational experiment.
