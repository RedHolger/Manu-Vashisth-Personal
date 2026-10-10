# SiliconCheck — requirements map

| Requirement (BUILD_PROMPTS rtl) | Test | Configs | Result |
|---|---|---|---|
| Reset | test_reset (empty/full/count) | 4x8, 16x32, 64x32 | pass |
| Ordering | test_ordered_fill_drain (seeded data) | all | pass |
| Overflow ignored | test_overflow_ignored (DEPTH + 4 extra, count pinned, order kept) | all | pass |
| Underflow ignored | test_empty_read_ignored | all | pass |
| Wraparound | test_wraparound_and_simultaneous (6xDEPTH+5 mixed steps, scoreboard + count) | all | pass |
| Backpressure | test_stream_order_with_backpressure (seeded, random stalls both sides) | all | pass |
| Overflow blocks ingress | test_overflow_blocks_ingress (s_ready drops, drain order) | all | pass |
| Regression JSON | results/regression.json | 6 runs | all pass |
| No timing closure | LIMITATIONS.md (no synthesis/device) | — | stated, unclaimed |
