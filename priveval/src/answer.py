"""Extractive answer pipeline with mode-dependent controls. No LLM."""
import re

import store
from retrieval import bm25

ABSTAIN = "No readable chunks for your tenant."
ALLOWLIST = {"quote_chunk"}
TOOL_RE = re.compile(r"TOOL\s+(\w+)")


def answer(db, mode, user, tenant, query):
    assert mode in ("baseline", "controls")
    visible = store.visible_chunks(db, mode, user, tenant)
    ranked = bm25(query, visible)
    by_id = {c["id"]: c for c in visible}
    if not ranked or ranked[0][1] <= 0:
        return {"answer": ABSTAIN, "tools": [], "chunk_id": None}
    cid = ranked[0][0]
    if mode == "controls" and not store.live_chunk(db, cid):
        return {"answer": ABSTAIN, "tools": [], "chunk_id": None}  # stale guard
    text = by_id[cid]["text"]
    tools = []
    for m in TOOL_RE.finditer(text):
        name = m.group(1)
        if mode == "controls":
            tools.append({"tool": name, "verdict": "rejected",
                          "reason": "not in read-only allowlist"})
        else:
            tools.append({"tool": name, "verdict": "executed"})
    return {"answer": text, "tools": tools, "chunk_id": cid}


def unauthorized_canaries(answer_text, requester_tenant):
    """Canaries in the answer whose home tenant the requester may not read."""
    found = [c for c in store.CANARIES if c in answer_text]
    return [c for c in found if store.CANARIES[c] != requester_tenant]
