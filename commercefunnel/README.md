# CommerceFunnel

A small event-analysis pipeline for a fictional shop. It follows the path from product views to purchases, then checks substitutions and on-time fulfilment. Every rate includes its denominator so a tiny sample cannot disappear behind a percentage.

The input has 26 event rows, including a replay. Ingestion removes duplicates before calculating funnels, weekly cohorts and uncertainty intervals.

## Generate the report

Python 3's standard library is sufficient. From this directory:

```bash
python3 -m unittest discover -s tests -v
python3 report.py
```

Read `results/report.json` for the calculations and `results/report.html` for the report. Metric definitions and hand calculations are in [SPEC.md](SPEC.md); the implementation is in `src/funnel.py`.

[experiment.md](experiment.md) proposes a follow-up experiment with primary and guardrail metrics. It has not been run. All input events are synthetic, so the report describes the fixture rather than a shop's actual conversion rate.
