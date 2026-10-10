"""PINN comparison for 1D heat (u_t = u_xx, Dirichlet 0, sin(pi x) IC).
Seeded MLP trained with Adam on CPU. Writes results/pinn.json.
Honest framing: compared against the FD baseline on accuracy AND cost;
no claim that the PINN wins (it should not on this smooth problem)."""
import json
import sys
import time

sys.path.insert(0, "src")
import numpy as np
import torch
import torch.nn as nn

SEED = 11
EPOCHS = 3000
N_COLLOC, N_BC, N_IC = 2000, 200, 200

torch.manual_seed(SEED)
np.random.seed(SEED)


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 32), nn.Tanh(),
            nn.Linear(32, 32), nn.Tanh(),
            nn.Linear(32, 1))

    def forward(self, xt):
        return self.net(xt)


def train(epochs=EPOCHS, seed=SEED, verbose=False):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = MLP()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    rng = np.random.default_rng(seed)
    xc = torch.from_numpy(rng.random((N_COLLOC, 1)).astype(np.float32))
    tc = torch.from_numpy(rng.random((N_COLLOC, 1)).astype(np.float32))
    xb = torch.from_numpy(rng.integers(0, 2, (N_BC, 1)).astype(np.float32))
    tb = torch.from_numpy(rng.random((N_BC, 1)).astype(np.float32))
    xi = torch.from_numpy(rng.random((N_IC, 1)).astype(np.float32))
    ic_target = torch.sin(torch.pi * xi)
    first, last = None, None
    t0 = time.perf_counter()
    for ep in range(epochs):
        opt.zero_grad()
        xt = torch.cat([xc, tc], dim=1).requires_grad_(True)
        u = model(xt)
        gu = torch.autograd.grad(u, xt, torch.ones_like(u), create_graph=True)[0]
        u_t, u_x = gu[:, 1:2], gu[:, 0:1]
        u_xx = torch.autograd.grad(u_x, xt, torch.ones_like(u_x), create_graph=True)[0][:, 0:1]
        loss_pde = ((u_t - u_xx) ** 2).mean()
        ub = model(torch.cat([xb, tb], dim=1))
        loss_bc = (ub ** 2).mean()
        ui = model(torch.cat([xi, torch.zeros_like(xi)], dim=1))
        loss_ic = ((ui - ic_target) ** 2).mean()
        loss = loss_pde + loss_bc + loss_ic
        loss.backward()
        opt.step()
        if ep == 0:
            first = loss.item()
        last = loss.item()
        if verbose and ep % 1000 == 0:
            print(f"ep {ep}: {loss.item():.3e}", flush=True)
    wall = time.perf_counter() - t0
    return model, {"first_loss": first, "last_loss": last, "wall_s": round(wall, 1)}


def evaluate(model):
    x = np.linspace(0, 1, 81, dtype=np.float32)
    t = np.full_like(x, 0.02)
    with torch.no_grad():
        u = model(torch.from_numpy(np.stack([x, t], 1))).numpy().ravel()
    exact = np.sin(np.pi * x) * np.exp(-np.pi ** 2 * 0.02)
    return float(np.sqrt(np.mean((u - exact) ** 2)))


if __name__ == "__main__":
    model, info = train(verbose=True)
    info["l2_at_t002"] = evaluate(model)
    info.update({"seed": SEED, "epochs": EPOCHS, "mlp": "2x32 tanh",
                 "optimizer": "Adam lr=1e-3", "device": "cpu"})
    json.dump(info, open("results/pinn.json", "w"), indent=2)
    print(json.dumps(info, indent=2))
