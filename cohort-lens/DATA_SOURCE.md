# Data source — P08 CohortLens (P08-04)

- Status: **no authorized product event stream has been supplied**.
  Synthetic fixtures remain the only measured evidence (`p08-01` … `p08-03`).
  The adapter below is ready; this file records exactly what is missing.
- Adapter: `real_data.py` — `load_csv_events(path)` reads
  `id,user,type,at,ingested_at[,segment]` (UTC-only, `signup|activate|active`
  only, no empty ids, no duplicate ids) and returns v1 events plus a segment
  map; `write_manifest()` freezes file name, source URL, license, retrieval
  time, sha256, bytes, rows, users, segment count and time range.
- Demo: `sample_events.csv` is a 4-row **synthetic adapter example**, not
  real product data and not licensed external data. It exists so the adapter
  path is tested without claiming real coverage.
- To supply a real stream, place the CSV at a private path (never commit
  private data), then run from `cohort-lens/`:

```sh
python3 -B -c "from real_data import write_manifest; print(write_manifest('PRIVATE.csv','https://example.invalid/source','Commercial — redistribution prohibited','2026-10-08T00:00:00Z','results/p08-04-real-data/PROVIDED-manifest.json'))"
python3 -B measure_p08_04.py --csv PRIVATE.csv --source-url https://example.invalid/source --license "Commercial — redistribution prohibited" --retrieved-at 2026-10-08T00:00:00Z --out results/p08-04-real-data
```

## Coverage (as of this checkpoint)

- Synthetic: 6-event funnel (P08-02/03), boundary fixtures (P08-01), 4-row
  adapter sample (this card). No product users, no production window.
- Real product events: 0 rows — none authorized.

## Privacy

- User ids are treated as pseudonymous labels. The adapter ingests no names,
  emails, free text or device identifiers. Do not supply exports containing
  direct identifiers without a documented lawful basis and minimization note.
- Sample and synthetic ids (`u1`, `demo-u1`) are fictitious.

## Retention

- The SQLite store is disposable per run (`:memory:` by default). The CSV is
  read, never copied into the repo by the adapter. Do not commit private
  exports, database files or credentials. Evidence keeps manifests and hashes,
  not row-level personal data.

## Limitations

- The adapter validates shape and timestamps; it cannot verify that an
  external export is complete, de-duplicated at source or correctly
  time-zoned. Record the export query, window and timezone with the manifest.
- No real-data recall/retention claim is made here. A future real stream
  needs its own coverage note plus a rerun of `measure_p08_01/02/03` on that
  stream before any product reading.
