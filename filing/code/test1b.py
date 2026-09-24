#!/usr/bin/env python3
"""Test 1b (T-818): does Jev need labelled examples to file my notes?
Pre-registration: test1b-preregistration.md. The examples are data/test1b-neighbours.jsonl,
built and checked (check_test1b_neighbours.py) before any call here.

    python3 test1b.py smoke                 # one Jev call with examples, on key note r-001
    python3 test1b.py run --arm B --label r1   # Jev with the 10 examples
    python3 test1b.py run --arm D --label r1   # Sonnet 5 with the same 10 examples
    python3 test1b.py run --arm C --label r1   # retrieval only, no model

Arms A and E are Test 1's own runs (results/routing-{jev,llm}-r*.jsonl), reused unchanged.
The calling code is test1.py's, imported, so model, pin, options, max tokens and the
confidence parsing are identical to Test 1. The only change is the state (the examples are
added) and one sentence added to the instructions. Scoring is analyse1b.py.
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict

import test1

HERE = test1.HERE
RESULTS = test1.RESULTS

INSTRUCTIONS = (test1.ROUTING_INSTRUCTIONS + " `examples` are similar notes already filed "
                "in this vault, each with the home it was filed to.")


def load_examples():
    rows = test1.load_rows(test1.DATA / "test1b-neighbours.jsonl")
    return {r["id"]: r["neighbours"] for r in rows}


EXAMPLES = None


def state(row):
    """Test 1's state plus the ten examples, highest score first."""
    return {"title": row["title"], "note": row["text"],
            "examples": [{"title": n["title"], "note": n["text"], "home": n["home"]}
                         for n in EXAMPLES[row["id"]]]}


def retrieval_only(row):
    """Arm C: most common home among the 10; ties to the higher summed BM25 score."""
    count, summed = Counter(), defaultdict(float)
    for n in EXAMPLES[row["id"]]:
        count[n["home"]] += 1
        summed[n["home"]] += n["score"]
    best = max(count, key=lambda h: (count[h], summed[h]))
    tied = [h for h in count if count[h] == count[best]]
    return {**test1.meta(row), "system": "retrieval", "model": "bm25-k10-majority",
            "served_model": "bm25-k10-majority (no model)", "predicted": best,
            "confidence": None, "votes": dict(count),
            "tie_broken_by_score": len(tied) > 1, "cost_usd": 0.0,
            "cost_basis": "no model call"}


def check_rows(rows):
    ids = [r["id"] for r in rows]
    if len(ids) != 83 or set(ids) != set(EXAMPLES):
        sys.exit("the key and the neighbour file do not cover the same 83 notes")


def smoke():
    from typesafe_sdk import TypeSafeClient
    rows = test1.load_rows(test1.DATA / "routing-key.jsonl")
    with TypeSafeClient() as client:
        rec = test1.jev_one(client, rows[0], test1.ROUTING_OPTIONS, INSTRUCTIONS, state)
    print(json.dumps(rec, indent=2))


def run(arm, label):
    rows = test1.load_rows(test1.DATA / "routing-key.jsonl")
    check_rows(rows)
    t0 = time.time()
    if arm == "B":
        out = test1.run_jev(rows, test1.ROUTING_OPTIONS, INSTRUCTIONS, state)
    elif arm == "D":
        out = test1.run_llm(rows, test1.ROUTING_OPTIONS, INSTRUCTIONS, state)
    else:
        out = [retrieval_only(r) for r in rows]
    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"test1b-{arm}-{label}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with open(dest, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps({**r, "task": "routing", "arm": arm, "run": label},
                                ensure_ascii=False) + "\n")
    errs = sum(1 for r in out if r.get("error") or not r.get("predicted"))
    print(f"wrote {dest.relative_to(HERE)}  {len(out)} rows, {errs} unusable, "
          f"{time.time() - t0:.0f}s")


def main():
    global EXAMPLES
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("smoke")
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=["B", "C", "D"], required=True)
    r.add_argument("--label", required=True)
    args = ap.parse_args()
    test1.load_env()
    EXAMPLES = load_examples()
    if args.cmd == "smoke":
        smoke()
    else:
        run(args.arm, args.label)


if __name__ == "__main__":
    main()
