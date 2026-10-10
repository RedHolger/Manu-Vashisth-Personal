"""Export TC-ResNet to ONNX + torch reference outputs. RUN WITH .venv-builds
(torch CPU, isolated from the KWS repo; original repo never touched).
Reads best.pt (read-only). Writes package/ inside this build dir only."""
import hashlib
import json
import sys

import numpy as np
import torch

sys.path.insert(0, "vendor")
from tc_resnet import TCResNet  # noqa: E402  (vendored copy, see PROVENANCE.md)

KWS = "/Users/manuvashistha/Developer/AnalogDevicesProjects/project2_keyword_spotting"
SEED = 7
N_MELS, T_FRAMES = 40, 101

cfg = {"num_classes": 10, "mel_bins": N_MELS, "base_filters": 48, "dropout": 0.3}
model = TCResNet(cfg)
sd = torch.load(f"{KWS}/experiments/saved_models/best.pt", map_location="cpu",
                weights_only=True)
model.load_state_dict(sd)
model.eval()

# (a) genuine mel of a synthetic 1 kHz sine via torchaudio, exact dataset params
import torchaudio  # noqa: E402

sr = 16000
t = torch.arange(sr, dtype=torch.float32) / sr
sine = torch.sin(2 * torch.pi * 1000 * t).unsqueeze(0)
mel_fn = torchaudio.transforms.MelSpectrogram(
    sample_rate=sr, n_fft=512, win_length=400, hop_length=160, n_mels=N_MELS)
mel = mel_fn(sine).unsqueeze(0)  # (1,1,40,T)
assert mel.shape[2] == N_MELS, mel.shape
T = mel.shape[3]
print("mel frames T =", T)

# (b) seeded random batch (same preprocessing geometry, synthetic content)
rng = np.random.default_rng(SEED)
rand = torch.from_numpy(rng.standard_normal((8, 1, N_MELS, T)).astype(np.float32))

inputs = {"sine_mel": mel, "rand_batch": rand}
with torch.no_grad():
    refs = {k: model(v).numpy() for k, v in inputs.items()}

dummy = torch.zeros(1, 1, N_MELS, T)
torch.onnx.export(model, dummy, "package/model.onnx", input_names=["mel"],
                  output_names=["logits"], opset_version=17, do_constant_folding=True)
import onnx  # noqa: E402

actual_opset = onnx.load("package/model.onnx").opset_import[0].version

np.savez("package/inputs.npz", **{k: v.numpy() for k, v in inputs.items()})
np.savez("package/torch_ref.npz", **refs)
meta = {
    "seed": SEED,
    "frames_T": T,
    "torch_version": torch.__version__,
    "opset_requested": 17,
    "opset_actual": actual_opset,
    "model_sha256": hashlib.sha256(open("package/model.onnx", "rb").read()).hexdigest(),
    "weights_sha256": "1d1c0e9309c5d9df99851e8fc79d5b22f0e312aa00afb320b00f5779eb93b372",
    "n_inputs": 1 + 8,
}
json.dump(meta, open("package/meta.json", "w"), indent=2)
print(json.dumps(meta, indent=2))
