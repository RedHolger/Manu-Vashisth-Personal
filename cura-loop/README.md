# CuraLoop — active learning on hidden labels

Test whether smart annotation beats random sampling — fairly. Labels live
behind a query-logged oracle; selectors see only label-free views. A
versioned store tracks every label change (author/time/version) under a fixed
budget, and random/uncertainty/diversity compete on matched budgets, seeds
and starting pools. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 43 tests
```

Recorded: 100/50 entity-split pool with 149/150 labels hidden; repeated
labels never inflate counts; learning curves over 3 seeds — diversity 0.967
> random 0.953 > uncertainty 0.933 (means; not clearly separable, reported
un-tuned). A consent-gated human-timing harness is included; measured human
time is kept strictly separate from the synthetic cost proxy, and no human
study has run (0 participants).

## Limits

Synthetic 2-D points; nearest-neighbour probabilities. Cost is an
acquisition proxy, not measured annotation time.
