"""Version-tagged chunk cache with two policies. The stale-cache scenario in
measure.py exercises a REAL cache: entries carry the version seen at fill
time, and revocation/version drift afterwards distinguishes the policies."""
import store


class ChunkCache:
    def __init__(self, policy):
        assert policy in ("naive", "validated")
        self.policy = policy
        self.entries = {}  # chunk_id -> {"version": v, "text": t}
        self.stats = {"hits": 0, "misses": 0, "stale_served": 0, "blocked": 0}

    def read(self, db, chunk_id):
        """Returns (text_or_None, outcome). Outcomes: hit, miss, stale-served
        (naive policy serving revoked/changed content), blocked (validated
        policy refusing revoked content)."""
        row = db.execute("SELECT version, revoked, text FROM chunks WHERE id=?",
                         (chunk_id,)).fetchone()
        if row is None:
            return None, "missing"
        version, revoked, text = row
        if self.policy == "naive":
            if chunk_id in self.entries:
                self.stats["hits"] += 1
                if revoked or self.entries[chunk_id]["version"] != version:
                    self.stats["stale_served"] += 1
                    return self.entries[chunk_id]["text"], "stale-served"
                return self.entries[chunk_id]["text"], "hit"
            self.stats["misses"] += 1
            self.entries[chunk_id] = {"version": version, "text": text}
            return text, "miss"
        # validated: version tag + revocation re-checked on every read
        if revoked:
            self.stats["blocked"] += 1
            self.entries.pop(chunk_id, None)
            return None, "blocked"
        if chunk_id in self.entries and self.entries[chunk_id]["version"] == version:
            self.stats["hits"] += 1
            return self.entries[chunk_id]["text"], "hit"
        self.stats["misses"] += 1
        self.entries[chunk_id] = {"version": version, "text": text}
        return text, "miss"
