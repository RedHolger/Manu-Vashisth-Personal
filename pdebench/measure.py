"""Repeatable measurement: convergence tables, residuals, runtime. Seed fixed."""
import json
import sys
import time
import tracemalloc

sys.path.insert(0, "src")
from heat1d import l2_error
from heat1d import solve as heat_solve
from poisson2d import solve as poisson_solve

SEED = 42
T_END = 0.02

heat_rows = []
for nx, dt in [(11, 0.004), (21, 0.001), (41, 0.00025), (81, 0.0000625)]:
    t0 = time.perf_counter()
    tracemalloc.start()
    x, u = heat_solve(nx, 1.0, dt, T_END)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    err = l2_error(u, x, T_END)
    heat_rows.append({"nx": nx, "dt": dt, "l2": err,
                      "wall_s": round(time.perf_counter() - t0, 4),
                      "peak_kb": round(peak / 1024, 1)})

poisson_rows = []
for n in [9, 17, 33]:
    t0 = time.perf_counter()
    out = poisson_solve(n, tol=1e-6, max_iter=40000)
    poisson_rows.append({"n": n, "iterations": out["iterations"],
                         "residual": out["residual"], "linf": out["linf"],
                         "wall_s": round(time.perf_counter() - t0, 3)})

report = {"seed": SEED, "t_end": T_END, "heat": heat_rows, "poisson": poisson_rows}
with open("results/measurements.json", "w") as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
