# PDEBench — SPEC (Milestone 1)

Scope: pure-Python (numpy) finite-difference baselines for role 36 (IBM PDE research).
No PDE background is claimed beyond building and measuring these documented solvers.

## Problems

1. **1D heat (FTCS explicit):** u_t = a u_xx on x in [0,1], Dirichlet u=0 at both ends,
   u(x,0) = sin(pi x), a = 1. Closed form: u(x,t) = sin(pi x) exp(-a pi^2 t).
   Stability: r = a dt/dx^2 <= 0.5. The solver raises `ValueError` when violated
   (negative-path test), so CFL blow-up is a checked error, not a silent NaN.
2. **2D Poisson (Jacobi):** -lap u = f on [0,1]^2, Dirichlet 0.
   Manufactured solution u = sin(pi x) sin(pi y) gives
   f = 2 pi^2 sin(pi x) sin(pi y). Stop on residual norm < tol or max iterations.

## Acceptance thresholds (this build)

- One-step stencil fixtures match hand calculations below to 1e-8 / 1e-6.
- Heat: L2 error vs closed form at t=0.02 decreases ~4x when dx halves (2nd-order in space).
- Poisson: discrete residual decreases monotonically; L_inf error shrinks with refinement.
- Boundary values stay exactly 0; negative inputs (negative nx, dt<=0) raise ValueError.
- Runtime/memory reported from a seeded repeatable run; seed recorded.

## Out of scope (explicit)

- PyTorch PINN comparison: IMPLEMENTED 2026-10-08 (src/pinn.py): seeded 2x32
  tanh MLP, Adam, 3000 epochs on CPU. Result: L2 2.4e-3 vs FD 2.05e-5 at the
  same probe — FD is ~100x more accurate here; the PINN is mesh-free. Both
  numbers reported; no winner claimed beyond this problem.
  Documented in LIMITATIONS.md, not claimed.
- No quantum-advantage or production-CFD claims.

## Hand-calculated fixtures

Heat one step, dx=0.25, r=0.25, u0=sin(pi x):
expected u^1 = [0, 0.60355339, 0.85355339, 0.60355339, 0].

Poisson one Jacobi sweep from zeros, h=0.5:
f(center) = 2 pi^2 ~= 19.739208802, expected center = h^2 f / 4 ~= 1.233700550.
