# EngineeringEvidence Demo — traceability tool (role 28)

Software-only requirements/revision/review/test traceability for a FICTIONAL
cabin mod. Not certification, not EASA competence — stated in every artifact.

## Setup (stdlib + pdflatex)

```
python -m unittest discover -s tests -v   # 6 tests (builds the PDF too)
python review_package.py                   # -> results/review.{json,tex,pdf}
```

## Layout

- `SPEC.md` (seeded defects), `src/trace.py`, `review_package.py`.
- `tests/test_trace.py`, `results/review.pdf`.
- `REQUIREMENTS.md`, `EVIDENCE.md`, `LIMITATIONS.md`.
