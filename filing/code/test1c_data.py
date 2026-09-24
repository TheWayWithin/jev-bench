#!/usr/bin/env python3
"""Test 1c (T-821): draw the held-out notes and their examples, before any Test 1c call.
Pre-registration: test1c-preregistration.md ("The two sets of notes").

    python3 test1c_data.py      # writes data/test1c-heldout.jsonl and data/test1c-neighbours.jsonl

The held-out set is drawn from the frozen Test 1b pool (data/test1b-pool.jsonl), excluding
every Test 1 note, with build_keys.py's stratified draw: homes in build_keys.HOMES order,
up to 15 per home, random.Random(821).sample over the home's notes sorted by path. Books and
efformism have no unused notes, so they contribute none. Neighbours use test1b_neighbours
exactly as Test 1b (same pool, BM25, k = 10, leave one out).
"""

import json
import random

import build_keys
import test1b_neighbours as nb

SEED = 821
PER_HOME = 15
HELDOUT = nb.DATA / "test1c-heldout.jsonl"
NEIGHBOURS = nb.DATA / "test1c-neighbours.jsonl"


def draw(pool, used):
    rng = random.Random(SEED)
    rows = []
    for home in build_keys.HOMES:
        cands = sorted((p for p in pool if p["home"] == home and p["path"] not in used),
                       key=lambda p: p["path"])
        if not cands:
            continue
        pick = cands if len(cands) <= PER_HOME else rng.sample(cands, PER_HOME)
        for p in sorted(pick, key=lambda p: p["path"]):
            rows.append({"id": f"h-{len(rows) + 1:03d}", "label": home, "path": p["path"],
                         "title": p["title"], "text": p["text"]})
    return rows


def main():
    pool = nb.load(nb.POOL)
    used = {k["path"] for k in nb.load(nb.KEY)}
    rows = draw(pool, used)
    HELDOUT.write_text(nb.serialise(rows), encoding="utf-8")
    nbrs = nb.compute(pool, rows)
    NEIGHBOURS.write_text(nb.serialise(nbrs), encoding="utf-8")
    dups = [r["id"] for r in nbrs if any(n["near_duplicate"] for n in r["neighbours"])]
    per = {}
    for r in rows:
        per[r["label"]] = per.get(r["label"], 0) + 1
    print(json.dumps({"heldout": len(rows), "per_home": per, "seed": SEED,
                      "heldout_sha256": nb.sha(HELDOUT), "neighbours_sha256": nb.sha(NEIGHBOURS),
                      "pool_sha256": nb.sha(nb.POOL),
                      "overlap_with_test1": sum(1 for r in rows if r["path"] in used),
                      "near_duplicate_ids": dups}, indent=2))


if __name__ == "__main__":
    main()
