# UserEvidence research protocol (P15-01) — v1, 2026-10-08

Two bounded formative studies. **No sessions, quotes or consent have been
collected; every row in this project is synthetic tooling fixtures until real
consenting participants are recruited. Nothing here is a finding about people.**

## Study A — OpsConsole incident comprehension (for P13)

- **Research question:** Can an on-call reader determine, from the OpsConsole
  incident view alone, whether an incident is stale vs actively updating, and
  which export it came from?
- **Participants:** 5–8 consenting adults with basic on-call or dashboard
  familiarity. Convenience sample; no population claim. Recruitment is
  BLOCKED (no channel authorized; no one recruited).
- **Neutral tasks (no leading language):**
  1. "Open the incident list. For incident INC-104, tell me what you see for
     its freshness."
  2. "This export was loaded 40 minutes ago. Show me where you would check
     that."
  3. "You need the source of the numbers on this chart. Walk me through how
     you would find it."
- **Banned phrasing (validator-enforced):** the script must not contain
  `you should`, `obviously`, `clearly shows`, `as you can see`, `just click`,
  `simply`, or any sentence that names the expected answer before the
  participant acts.

## Study B — StudyPath planning (for P14)

- **Research question:** Can a planner user add a study block that conflicts
  with a prerequisite chain, and does the planner make the conflict visible
  without losing saved progress?
- **Participants:** 5–8 consenting students/planners. Convenience sample.
  Recruitment BLOCKED (same as Study A).
- **Neutral tasks:**
  1. "Add a 90-minute study block for Thursday evening."
  2. "This block overlaps a prerequisite. Tell me what the planner shows."
  3. "Import this course file. Tell me what happened to your existing plan."
- **Banned phrasing:** same list as Study A.

## Pilot script (human pilot BLOCKED; tooling pilot done)

1. Read one task aloud verbatim. 2. Observe silently; do not help. 3. Record:
   task id, success (bool), seconds (stopwatch), one verbatim observation,
   codes (from the codebook, added after — never during). 4. Debrief with one
   neutral prompt ("Anything surprising?"). The tooling pilot runs this exact
   record shape through the summarizer on synthetic fixtures
   (`protocol.pilot_tooling()`); a human pilot needs consenting participants
   and is BLOCKED.

## Ethics and university requirements

- Written consent before any recording (`CONSENT_FORM.md`); participation is
  voluntary and withdrawable with deletion of records.
- Pseudonymous ids (`P-001`…); no names, contact info or identifying detail
  in any record. Anonymization happens at capture, not after.
- If used academically, follow the university's human-subjects requirements
  (IRB/ethics review) BEFORE recruitment. This protocol does not substitute
  for that approval.
- Never fabricate sessions, quotes or consent. Synthetic fixtures are tagged
  `synthetic: true` and excluded from every human metric.

## From observations to changes

Observations are coded against `CODEBOOK.md` (observation vs interpretation
kept separate; contradictions retained). Findings trace to design changes in
P13/P14 only after a real study runs. Participant counts and observation
counts are reported separately. A second coder reviews a sample when one is
available (currently none — recorded, not assumed).
