# InferenceParity Bench

A CPU inference check for a TC-ResNet keyword-spotting model exported to ONNX. The benchmark compares ONNX Runtime output with saved PyTorch reference output and measures local inference latency.

The input package includes a mel spectrogram derived from a synthetic sine wave and a seeded random batch. These inputs check export consistency; they do not measure recognition accuracy on real speech.

## Use the saved package

Install NumPy and ONNX Runtime in a Python 3 environment, then run from this directory:

```bash
python3 bench.py
python3 -m unittest discover -s tests -v
```

The benchmark reads `package/` and writes `results/bench.json`. Check [EVIDENCE.md](EVIDENCE.md) for recorded parity and timing results.

## Re-export the model

`export_package.py` requires PyTorch, torchaudio and ONNX. It currently reads a checkpoint from the author's keyword-spotting checkout through the `KWS` path constant. Supply that checkpoint and adjust the path before running the exporter. [PROVENANCE.md](PROVENANCE.md) records the model and weight provenance.

NPU execution has not been tested. The project directory retains its original name, but the reported results are CPU results.
