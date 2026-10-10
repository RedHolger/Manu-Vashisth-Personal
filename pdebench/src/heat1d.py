"""1D heat equation, FTCS explicit scheme. stdlib + numpy only."""
import numpy as np


def initial_sine(nx: int) -> tuple[np.ndarray, float]:
    if nx < 3:
        raise ValueError("nx must be >= 3")
    x = np.linspace(0.0, 1.0, nx)
    return np.sin(np.pi * x), float(x[1] - x[0])


def step(u: np.ndarray, r: float) -> np.ndarray:
    v = u.copy()
    v[1:-1] = u[1:-1] + r * (u[2:] - 2.0 * u[1:-1] + u[:-2])
    v[0] = 0.0
    v[-1] = 0.0
    return v


def solve(nx: int, alpha: float, dt: float, t_end: float) -> tuple[np.ndarray, np.ndarray]:
    if dt <= 0 or t_end <= 0:
        raise ValueError("dt and t_end must be positive")
    u, dx = initial_sine(nx)
    r = alpha * dt / dx**2
    if r > 0.5:
        raise ValueError(f"CFL violated: r={r:.4f} > 0.5 (dt={dt}, dx={dx})")
    x = np.linspace(0.0, 1.0, nx)
    n_steps = int(round(t_end / dt))
    for _ in range(n_steps):
        u = step(u, r)
    return x, u


def analytic(x: np.ndarray, t: float, alpha: float = 1.0) -> np.ndarray:
    return np.sin(np.pi * x) * np.exp(-alpha * np.pi**2 * t)


def l2_error(u: np.ndarray, x: np.ndarray, t: float, alpha: float = 1.0) -> float:
    return float(np.sqrt(np.mean((u - analytic(x, t, alpha)) ** 2)))
