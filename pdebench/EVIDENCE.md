# PDEBench — EVIDENCE (measured 2026-10-08)

Environment: macOS arm64, Python 3.14.7, numpy 2.2.6 (project venv
`.venv-builds`), seed 42. No other dependencies.

## Commands (all exit 0)

- `python -m unittest discover -s tests -v` → 9 tests OK (fixtures, convergence,
  boundaries, CFL/negative-input errors).
- `python measure.py` → `results/measurements.json` (reproduced twice, identical values).

## Measured outputs

1D heat (FTCS, a=1, t=0.02, closed-form sine reference):
nx=11 L2=1.28e-3; nx=21 L2=3.23e-4; nx=41 L2=8.15e-5; nx=81 L2=2.05e-5.
Error ratio per grid halving: 3.96 / 3.97 / 3.98 — second-order in space.
Wall time 0.0001–0.0021 s; peak traced memory 1.8–4.0 kB.

2D Poisson (Jacobi, manufactured sine, tol=1e-6):
n=9: 206 iters, residual 9.3e-7, L_inf 1.30e-2.
n=17: 834 iters, residual 9.9e-7, L_inf 3.22e-3.
n=33: 3344 iters, residual 1.0e-6, L_inf 8.03e-4.
L_inf ratio per refinement: 4.02 / 4.01 — second-order; residual monotone decreasing.

## Claim basis for CV 36 (role 36 only)

- "Built 1D heat and 2D Poisson finite-difference baselines against analytic/manufactured solutions; measured second-order grid convergence (L2/L_inf error ~4x per refinement) with residual, runtime and memory reports."
- "Checked CFL stability as a raised error, pinned Dirichlet boundaries, and recorded seed/environment; plus a seeded PINN comparison (see Extension 2026-10-08 below)."

## Extension 2026-10-08 (PINN comparison implemented)
- `src/pinn.py` (seed 11, 2x32 tanh, Adam 1e-3, 3000 epochs, CPU 9 s):
  training loss 0.65 -> 2.7e-4; L2 at t=0.02 = 2.4e-3 vs FD 2.05e-5.
  Honest reading: FD ~100x more accurate on this smooth problem; PINN is
  mesh-free. Both numbers in results/pinn.json; no winner declared.
- Claim basis addition for CV 36: "plus a seeded PINN comparison (L2 2.4e-3
  vs FD 2.05e-5 on the same probe; FD more accurate here)."
