# OpsConsole — LIMITATIONS

- All data synthetic and in-memory (server restart resets state); not
  FlowLedger/RecoverOps production code, no live-service exposure.
- Auth is a demo `X-Role` header, not real identity; audit is in-process.
- UI exercised via unit-tested logic + production build, not browser
  end-to-end runs (no browser automation installed).
- Local-machine results; npm registry packages pinned in package.json.
- Supports role 21 only as dashboard/adapter demo work.
