"""From-scratch GLMs: Poisson IRLS (log link + offset) and log-scale OLS."""
import numpy as np

COLS = ["intercept", "young", "urban", "suv"]


def design(rows):
    X = np.column_stack([np.ones(len(rows)), rows["young"], rows["urban"], rows["suv"]])
    return X


def poisson_irls(X, y, offset, tol=1e-8, max_iter=100):
    """Poisson GLM, log link, known offset. Solves min ||sqrt(W)(z - Xb - o)||^2
    each step, i.e. normal equations XtWX b = XtW(z - o). Returns
    (beta, se, info). Raises on invalid inputs or non-convergence."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    offset = np.asarray(offset, dtype=float)
    if not (X.shape[0] == y.shape[0] == offset.shape[0]):
        raise ValueError("mismatched lengths")
    if np.any(y < 0):
        raise ValueError("Poisson counts must be >= 0")
    if not np.all(np.isfinite(offset)):
        raise ValueError("offset must be finite (exposure must be positive)")
    beta = np.zeros(X.shape[1])
    n_iter = max_iter
    for i in range(max_iter):
        eta = X @ beta + offset
        mu = np.exp(np.clip(eta, -30, 30))
        w = mu
        z = eta + (y - mu) / np.maximum(mu, 1e-12)
        target = z - offset  # offset lives outside X @ beta
        XtWX = (X * w[:, None]).T @ X
        XtWz = (X * w[:, None]).T @ target
        step = np.linalg.solve(XtWX, XtWz)
        if np.max(np.abs(step - beta)) < tol:
            beta = step
            n_iter = i + 1
            break
        beta = step
    else:
        raise RuntimeError(f"IRLS did not converge in {max_iter} iterations")
    # covariance from the FINAL fitted means (not a stale loop weight)
    mu = np.exp(np.clip(X @ beta + offset, -30, 30))
    cov = np.linalg.inv((X * mu[:, None]).T @ X)
    return beta, np.sqrt(np.diag(cov)), {"n_iter": n_iter}


def ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(1, len(y) - X.shape[1])
    s2 = float(resid @ resid / dof)
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta, np.sqrt(np.diag(cov))


def poisson_deviance(y, mu):
    mu = np.maximum(mu, 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        ll = np.where(y == 0, 0.0, y * np.log(y / mu))
    return 2.0 * float(np.sum(ll - (y - mu)))
