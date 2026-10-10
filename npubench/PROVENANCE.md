# PROVENANCE — npubench sources

- `vendor/tc_resnet.py`: verbatim copy of
  `/Users/manuvashistha/Developer/AnalogDevicesProjects/project2_keyword_spotting/models/tc_resnet.py`
  (TC-ResNet per Choi et al. 2019; user-owned repo, reused with attribution).
  sha256 `6989ecfb6f6ddcf25a787362a28a0edf884dc238452546cc121e4a08925b0c14`.
  Original repository NOT modified.
- Weights `best.pt` (state_dict, 316,154 params): read-only load at export time from
  `.../project2_keyword_spotting/experiments/saved_models/best.pt`,
  sha256 `1d1c0e9309c5d9df99851e8fc79d5b22f0e312aa00afb320b00f5779eb93b372`.
- Preprocessing params from that repo's `configs/dataset.yaml`
  (16 kHz, n_fft 512, hop 160, win 400, n_mels 40).
- Everything else in this directory is newly written for this build.
