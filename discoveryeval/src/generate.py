"""Generate the frozen synthetic catalog + queries + qrels (seed 11).
Run once; outputs committed under datasets/. Asserts the overlap contracts."""
import json
import random

SEED = 11
rng = random.Random(SEED)

STOP = {"and", "with", "for", "the", "a", "of", "in", "to", "per"}

CATS = {
    "gate-valve": {
        "terms": ["valve", "gate", "flow", "brass", "pn16", "flanged", "shutoff"],
        "syn": ["flow controller", "shutoff unit"],
        "fills": ["body", "stem", "handwheel", "seat", "pressure rated"],
    },
    "centrifugal-pump": {
        "terms": ["pump", "centrifugal", "impeller", "head", "3kw", "volute", "suction"],
        "syn": ["fluid mover", "liquid transfer unit"],
        "fills": ["motor", "seal", "bearing housing", "discharge", "cavitation free"],
    },
    "proximity-sensor": {
        "terms": ["sensor", "proximity", "inductive", "npn", "8mm", "detection", "switch"],
        "syn": ["nearness detector", "presence switch"],
        "fills": ["cable", "led indicator", "threaded barrel", "ip67", "response"],
    },
    "ball-bearing": {
        "terms": ["bearing", "ball", "608zz", "shielded", "radial", "greased", "bore"],
        "syn": ["rotary support", "friction reducer"],
        "fills": ["steel", "cage", "clearance", "speed rated", "sealed"],
    },
    "control-cable": {
        "terms": ["cable", "control", "shielded", "4core", "pvc", "flexible", "wiring"],
        "syn": ["signal cord", "command wire"],
        "fills": ["copper", "jacket", "bend radius", "uv resistant", "metre reel"],
    },
    "hydraulic-filter": {
        "terms": ["filter", "hydraulic", "10micron", "cartridge", "return", "element", "bypass"],
        "syn": ["oil strainer", "fluid purifier"],
        "fills": ["housing", "indicator", "flow rate", "seals", "service life"],
    },
}


def content_terms(words):
    return {w for w in words if w not in STOP}


products = []
pid = 0
by_cat = {}
for cat, d in CATS.items():
    by_cat[cat] = []
    for i in range(10):
        pid += 1
        t = rng.sample(d["terms"], 3)
        f = rng.sample(d["fills"], 3)
        title = f"{t[0]} {t[1]} {cat.split('-')[0]}-{100 + pid}"
        desc = f"{' '.join(t)} with {' '.join(f)}. Suitable for industrial {cat.replace('-', ' ')} service."
        p = {"id": f"P{pid:03d}", "title": title, "description": desc, "category": cat,
             "terms": sorted(content_terms((title + " " + desc).lower().replace("-", " ").split()))}
        products.append(p)
        by_cat[cat].append(p)

queries, qrels = [], {}

# 18 standard queries: 2-3 sampled terms from 1-2 same-category targets
q = 0
for _ in range(18):
    cat = rng.choice(list(CATS))
    targets = rng.sample(by_cat[cat], k=rng.choice([1, 1, 2]))
    pool = sorted({t for p in targets for t in p["terms"]})
    qw = rng.sample(pool, k=min(3, len(pool)))
    q += 1
    qid = f"Q{q:02d}"
    queries.append({"id": qid, "text": " ".join(qw), "cold": False})
    qrels[qid] = [p["id"] for p in targets]

# 6 cold queries: synonym-only wording, zero content-term overlap with targets.
# Synonym phrases are scrubbed of any category term first (e.g. "shutoff unit"
# would otherwise leak "shutoff" into a gate-valve query).
for _ in range(6):
    cat = rng.choice(list(CATS))
    targets = rng.sample(by_cat[cat], k=1)
    clean = [" ".join(w for w in ph.split() if w not in CATS[cat]["terms"])
             for ph in CATS[cat]["syn"]]
    clean = [c for c in clean if c]
    synwords = rng.choice(clean).split()
    q += 1
    qid = f"Q{q:02d}"
    queries.append({"id": qid, "text": " ".join(synwords), "cold": True})
    qrels[qid] = [p["id"] for p in targets]

# contracts
pterms = {p["id"]: set(p["terms"]) for p in products}
for qu in queries:
    qt = content_terms(qu["text"].lower().replace("-", " ").split())
    ov = [len(qt & pterms[r]) for r in qrels[qu["id"]]]
    if qu["cold"]:
        assert all(o == 0 for o in ov), (qu, ov)
    else:
        assert any(o >= 2 for o in ov), (qu, ov)

json.dump(products, open("datasets/catalog.json", "w"), indent=1)
json.dump(queries, open("datasets/queries.json", "w"), indent=1)
json.dump(qrels, open("datasets/qrels.json", "w"), indent=1)
print(f"products={len(products)} queries={len(queries)} "
      f"cold={sum(1 for x in queries if x['cold'])}")
