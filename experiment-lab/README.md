# ExperimentLab — honest randomized experiments

Declare the estimand, randomize, and report uncertainty — with A/A
validation proving the machinery is calibrated before any effect is
claimed. Includes a one-covariate adjustment compared against the fixed
baseline. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 32 tests
python3 -B measure_p07_01.py   # (measurement scripts included per card)
```

Recorded: 500+ predeclared A/A simulations with Monte Carlo uncertainty
(false-positive rate, coverage, power); hand-computed SQL fixtures validate
every denominator; sample-ratio checks gate causal claims.

## Limits

Single-machine simulations, not production experiment results. No causal
claims for non-randomized data; covariate adjustment is one predeclared
comparison, not a modeling result.
