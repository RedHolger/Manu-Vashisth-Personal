# Codebook — UserEvidence (v1, tooling only)

Codes are applied AFTER a session, never during. The observation column is
verbatim participant behavior; the interpretation column is analyst language
and is stored separately so the two can never be confused.

| code | meaning | example observation (synthetic) |
|---|---|---|
| `visibility` | key state (freshness, conflict, provenance) was/wasn't seen | "did not mention the stale label" |
| `conflict-clarity` | the conflict/overlap message was/wasn't understood | "read the overlap warning aloud" |
| `provenance` | source/export trace was/wasn't found | "opened the export manifest" |
| `progress-safety` | saved work felt safe/endangered | "hesitated before importing" |
| `wording` | label text misled or helped | "called the cutoff 'expiry'" |

## Rules

1. **Observation ≠ interpretation.** `observation` is what happened;
   `analyst_note` (separate field, added later) is what it might mean. A row
   with an interpretation but no verbatim observation is invalid.
2. **Contradictions are retained.** The same code with opposite outcomes
   (one participant succeeds, another fails) is flagged as a contradiction
   and reported, never averaged away or dropped.
3. **Participant count ≠ observation count.** One participant can produce many
   observations; findings report both denominators separately.
4. **Second coder.** A sample is re-coded independently when a second coder is
   available. Currently none is available — recorded as pending, not assumed.
