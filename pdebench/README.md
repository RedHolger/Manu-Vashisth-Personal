# PDEBench

Finite-difference solvers for the 1D heat equation and 2D Poisson equation, with a separate physics-informed neural network comparison. Known analytic and manufactured solutions make it possible to measure error instead of judging a solver by its plots.

The heat solver uses an explicit FTCS scheme and rejects unstable time steps. The Poisson solver uses Jacobi iteration with a residual stopping condition. Measurements record convergence, runtime and memory use.

## Run the finite-difference baseline

From this directory, using Python 3:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python measure.py
```

Read `results/measurements.json` for the convergence tables. The solver implementations are in `src/heat1d.py` and `src/poisson2d.py`.

## PINN comparison

With PyTorch installed in the same environment, run `python src/pinn.py`. It trains a seeded MLP on the heat-equation residual and boundary/initial conditions, then writes `results/pinn.json`.

The saved comparison favors finite differences on this smooth problem. That is a result for this setup, not a general ranking of numerical methods. [SPEC.md](SPEC.md) defines the problems; [EVIDENCE.md](EVIDENCE.md) records the runs.
