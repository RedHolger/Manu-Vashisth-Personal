"""2D Poisson equation, Jacobi iteration against a manufactured solution."""
import numpy as np


def manufactured(n: int) -> tuple[np.ndarray, np.ndarray, float]:
    if n < 3:
        raise ValueError("n must be >= 3")
    x = np.linspace(0.0, 1.0, n)
    h = float(x[1] - x[0])
    xx, yy = np.meshgrid(x, x)
    u_exact = np.sin(np.pi * xx) * np.sin(np.pi * yy)
    f = 2.0 * np.pi**2 * u_exact
    return f, u_exact, h


def jacobi_sweep(u: np.ndarray, f: np.ndarray, h: float) -> np.ndarray:
    v = u.copy()
    v[1:-1, 1:-1] = (
        u[:-2, 1:-1] + u[2:, 1:-1] + u[1:-1, :-2] + u[1:-1, 2:] + h**2 * f[1:-1, 1:-1]
    ) / 4.0
    v[0, :] = 0.0
    v[-1, :] = 0.0
    v[:, 0] = 0.0
    v[:, -1] = 0.0
    return v


def residual(u: np.ndarray, f: np.ndarray, h: float) -> float:
    lap = (u[:-2, 1:-1] + u[2:, 1:-1] + u[1:-1, :-2] + u[1:-1, 2:] - 4.0 * u[1:-1, 1:-1]) / h**2
    return float(np.sqrt(np.mean((lap + f[1:-1, 1:-1]) ** 2)))


def solve(n: int, tol: float = 1e-6, max_iter: int = 20000) -> dict:
    if tol <= 0 or max_iter <= 0:
        raise ValueError("tol and max_iter must be positive")
    f, u_exact, h = manufactured(n)
    u = np.zeros_like(f)
    res0 = residual(u, f, h)
    history = [res0]
    it = 0
    while it < max_iter:
        u = jacobi_sweep(u, f, h)
        it += 1
        r = residual(u, f, h)
        history.append(r)
        if r < tol:
            break
    err_inf = float(np.max(np.abs(u - u_exact)))
    return {"u": u, "iterations": it, "residual": history[-1],
            "residual0": res0, "linf": err_inf, "h": h, "monotone": all(
                b <= a + 1e-15 for a, b in zip(history, history[1:]))}
