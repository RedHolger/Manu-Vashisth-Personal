# StudyPath design portfolio — P14-03 (decisions, not screenshots)

**No user research was conducted; no interviews or personas exist or are
presented. Every decision below is author judgment, stated as such, with the
alternative it beat and why.** Editable sources: `index.html`, `style.css`,
`app.js`, `model.js`, `schedule.js` and `wireframe.svg` (all text, all in
this folder).

## Decisions

1. **Topic cards, not a calendar grid.** Chose a vertical card list (title +
   requires + one toggle button each). Alternative: week-grid calendar.
   Rejected — grids need drag or complex grid-keyboard support this project
   cannot verify without a browser; cards tab linearly and read cleanly.
2. **Derived lock state, no separate lock flag.** A topic is actionable iff
   prerequisites are done (computed in `toggle`); the UI shows the reason
   ("Complete prerequisites first") instead of disabling silently.
   Alternative: disabled buttons. Rejected — disabled controls hide the
   reason; an attempted action that explains is more usable.
3. **Inline errors, state never erased.** Import/parse/toggle failures write
   to `#message` (role=status) and keep previous data (tested: invalid import
   returns the old plan). Alternative: modal alerts. Rejected — modals trap
   focus and risk data loss on dismiss.
4. **localStorage with safe fallback.** Stored JSON is re-validated on load;
   corrupt stores fall back to the example WITHOUT erasing storage (message
   says so). Alternative: wipe-and-reset. Rejected — destroys user progress.
5. **Scheduling as conflict visibility, not auto-resolve.** `planBlock()`
   reports clashes; the user moves the block. Alternative: auto-shift.
   Rejected — silent rescheduling loses user intent.
6. **Mandatory vs optional in data, not just prose.** Optional topics carry no
   `requires` links and nothing requires them, so the model cannot block on
   them by construction (not by convention).

## Accessibility reasoning (static; browser/AT BLOCKED)

Native buttons with `aria-pressed`, `role="status"` live region, visible
focus (shared pattern), text (not color) for state. Real keyboard/SR testing
needs a browser and is BLOCKED — the reasoning above is design intent, not
verification.

## Rejected designs (preserved)

- Calendar grid (keyboard cost). - Modal confirmations (focus/data risk).
- Auto-advance on completion (surprise). - University-specific catalog import
  (no source inspected; generic curriculum only).
