# UserEvidence — usability research instruments

Everything needed to run two small formative studies (incident comprehension
and study planning) — and nothing pretending the studies ran. A two-study
protocol with neutral tasks, a consent form, a codebook, consent-gated
pseudonymous capture (refusals consume nothing, PII refused), analysis that
retains contradictions and separates participant from observation counts, and
retest comparison that refuses population claims. Pure Python, stdlib only.

## Run it

```sh
python3 -B -m unittest discover -p 'test_*.py'   # 19 tests
```

Status: instruments verified on synthetic fixtures; **0 participants, 0
sessions, 0 findings.** Academic use additionally needs human-subjects
approval (none obtained — stated in the protocol). The tooling is ready the
moment people are.

## Limits

Starter guards (banned-phrase and PII-shape scans) are not bias/PII
guarantees; real pilots need human review. The codebook expects emergent
revision once real sessions exist.
