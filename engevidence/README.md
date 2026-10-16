# EngineeringEvidence

A requirements-traceability tool built around a fictional aircraft cabin modification. It links requirements, revisions, reviews and test evidence, then identifies orphan requirements, conflicting records and missing evidence.

The output is a review package that lets a reader follow a requirement back to its supporting records. It is a software demonstration, not an aircraft certification package.

## Build the review package

Requirements: Python 3 and `pdflatex` on PATH.

```bash
python3 -m unittest discover -s tests -v
python3 review_package.py
```

The script writes `results/review.json`, `results/review.tex` and `results/review.pdf`. The tests also exercise PDF generation.

`src/trace.py` contains the checks. [SPEC.md](SPEC.md) describes the deliberately seeded defects, and [EVIDENCE.md](EVIDENCE.md) records the saved test results.
