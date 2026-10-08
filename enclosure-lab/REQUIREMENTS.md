# Enclosure requirements — P22-01 (ASSUMED dimensions, not authoritative)

**Status: ASSUMED.** No manufacturer drawing was available, so every board
dimension below is an ASSUMPTION for design exercise only. Nothing here has
been checked against a real board. Authoritative dimensions are BLOCKED
(supply a board drawing to unblock). A fit claim on these numbers would be
fabrication; none is made.

## Assumed board (all values ASSUMED, mm)

| item | value | tolerance | source |
|---|---|---|---|
| board width (X) | 85.0 | ±0.2 | ASSUMED |
| board length (Y) | 56.0 | ±0.2 | ASSUMED |
| board height incl. tallest part (Z) | 20.0 | ±0.5 | ASSUMED |
| mounting holes (4×, M2.5) at (3.5, 3.5) from each corner | ⌀2.75 ±0.05 | ASSUMED positions ±0.1 |
| connector keep-out A (USB edge, X=85 side) | 15 × 16 × 16 | ASSUMED |
| connector keep-out B (power edge, Y=0 side) | 12 × 9 × 11 | ASSUMED |

## Enclosure requirements

- R1: board + 2.0 mm clearance per side; 2.0 mm walls; 3.0 mm base.
- R2: lid with 4× M3 screws into heat-set inserts; lid gap ≤ 0.3 mm (assumed).
- R3: cutouts for keep-outs A/B with +0.5 mm extra clearance (assumed).
- R4: 4× brass standoffs (M2.5, 6 mm) under mounting holes (assumed BOM).
- R5: open-top v1 (no lid) vs lidded v2 compared in P22-03.

## Thermal assumptions (NOT a simulation)

- Assumed 3 W board dissipation, natural convection, 25 °C ambient
  (all ASSUMED). No mesh, no solver, no validated result. Any thermal claim
  beyond "assumed boundary conditions documented" is refused by the P22-03
  claim scan.

## Authoritative gate (BLOCKED)

To unblock: supply the board manufacturer's drawing (PDF/DXF) with
dimensions, tolerances, hole positions and connector envelopes. Then re-issue
this file as AUTHORITATIVE with the drawing id, and re-run all geometry
checks. Until then every dimension stays ASSUMED.
