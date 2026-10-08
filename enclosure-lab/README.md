# EnclosureLab — parametric enclosure CAD on assumed dimensions

A design exercise for an edge-device enclosure: assumed board spec with
tolerances and connector keep-outs (every value tagged ASSUMED — no
manufacturer drawing exists), editable OpenSCAD (open-top v1, lidded v2 with
bosses and cutouts), a dimensioned SVG drawing, an assumed BOM, a v1/v2
comparison that refuses validation language (checked by a claim scanner),
and a prototype fit procedure whose worksheet is honestly blank. Pure
Python (generator), stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 15 tests
```

Recorded: cavity clearances meet the assumed rules on paper; thermal entries
are documented assumptions with boundary conditions (no mesh, no solver, no
result); zero measurements taken, zero fabricated.

## Limits

Assumed dimensions are not authoritative; renderings are not validation;
thermal assumptions are not simulation. Fit needs a fabricated prototype and
instruments, neither present here.
