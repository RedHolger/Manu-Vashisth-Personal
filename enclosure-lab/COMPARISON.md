# Design comparison v1 vs v2 — P22-03 (assumptions, not validation)

Both revisions are geometric designs on ASSUMED dimensions. A rendering is
not validation; no simulation was run; no fit was measured. Thermal entries
are boundary-condition assumptions, explicitly unvalidated.

## Fit (assumed cavity vs assumed board)

- Cavity clearances: X +4.0 / Y +4.0 / Z +5.0 mm over the assumed board
  (R1 needs 2.0/side — met on paper, NOT a fit claim).
- v1 and v2 share the cavity; fit is identical between revs on assumed dims.
- Cutouts A/B lie within walls with +0.5 assumed extra (checked numerically).
- Authoritative check BLOCKED (no manufacturer drawing).

## Assembly (untested, no prototype)

- v1: 2 steps (place, 4× M2.5). v2: 4 steps (+ lid seat, 4× M3).
- v2 BOM: base, lid, 4× M3, 4× standoffs, 4× inserts (all assumed, unsourced).
- Lid gap 0.3 assumed; alignment untested.

## Thermal (assumptions with boundary conditions, NOT a simulation)

- Assumed: 3 W, natural convection, 25 °C ambient (all ASSUMED).
- v1 open top is assumed to convect better; v2 lid is assumed to trap heat.
- No mesh, no solver, no sensitivity study, no result. Any reading of these
  assumptions as validated thermal performance would be wrong; this document
  does not make that claim and the P22-03 claim scan refuses it.

## Verdict (design-stage only)

v2 is the fuller design (lid, bosses, cutouts, BOM) at the cost of 2 extra
assembly steps and assumed-worse thermals. Neither rev is validated for fit,
assembly or thermals. Prototype + authoritative dims decide.
