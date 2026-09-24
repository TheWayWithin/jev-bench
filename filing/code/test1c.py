#!/usr/bin/env python3
"""Test 1c (T-821): escalation, narrow questions, and one bounded rewording round.
Pre-registration: test1c-preregistration.md.

    # rewording round on the working set W (the 83 Test 1 notes); rounds are not results
    python3 test1c.py run --set W --arm F --label round0
    python3 test1c.py run --set W --arm B --questions data/test1c-round1.json --label round1

    # held-out set H (75 fresh notes), only after data/test1c-questions.json is frozen
    python3 test1c.py run --set H --arm C --label r1
    python3 test1c.py run --set H --arm B --label r1      # also D, F; G reads the frozen file

A question set is JSON: {"shape": "choice" | "nouls", "instructions": str, "options": {home: text}}.
The baseline set is Test 1b's exactly (test1b.INSTRUCTIONS, test1.ROUTING_OPTIONS). The Choice
and Claude calls are test1.py's own functions; only the Noul call is new here.
"""

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
from collections import Counter, defaultdict

import test1
import test1b

HERE, DATA, RESULTS = test1.HERE, test1.DATA, test1.RESULTS
THRESHOLD = 0.80          # keep line, fixed
SECOND_BAR = 0.50         # Noul shapes: a second home at or above this means "fits two", pass on
FROZEN = DATA / "test1c-questions.json"
SETS = {
    "W": (DATA / "routing-key.jsonl", DATA / "test1b-neighbours.jsonl"),
    "H": (DATA / "test1c-heldout.jsonl", DATA / "test1c-neighbours.jsonl"),
}


def base_questions(shape):
    return {"shape": shape, "instructions": test1b.INSTRUCTIONS,
            "options": dict(test1.ROUTING_OPTIONS)}


def noul_text(q, home):
    return f"{q['instructions']} Should this note be filed to `{home}`? {q['options'][home]}"


def make_state(examples):
    def state(row):
        return {"title": row["title"], "note": row["text"],
                "examples": [{"title": n["title"], "note": n["text"], "home": n["home"]}
                             for n in examples[row["id"]]]}
    return state


def jev_nouls_one(client, row, q, state_fn):
    from typesafe_sdk import Noul
    homes = list(q["options"])
    questions = {h: Noul(instructions=noul_text(q, h)) for h in homes}
    started = time.perf_counter()
    try:
        resp = client.system_one(state=state_fn(row), questions=questions, model=test1.JEV_MODEL)
    except Exception as exc:
        return {**test1.meta(row), "system": "jev", "model": test1.JEV_MODEL, "error": repr(exc)}
    nouls = {h: float(resp.answers[h].noul) for h in homes}
    ranked = sorted(homes, key=lambda h: (-nouls[h], homes.index(h)))  # ties: option order
    top, second = nouls[ranked[0]], nouls[ranked[1]]
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "input_tokens", 0) or 0
    return {
        **test1.meta(row), "system": "jev", "model": test1.JEV_MODEL,
        "served_model": getattr(resp, "model", None),
        "predicted": ranked[0], "confidence": top, "second": second,
        "keep": top >= THRESHOLD and second < SECOND_BAR, "nouls": nouls,
        "seconds": round(time.perf_counter() - started, 3),
        "input_tokens": tin, "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cost_usd": tin / 1e6 * test1.JEV_PRICE_PER_MTOK,
        "cost_basis": "price table: input tokens x $0.042/MTok, output free",
    }


def run_jev(rows, q, state_fn):
    from typesafe_sdk import TypeSafeClient
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set in tools/jev-bench/.env")
    with TypeSafeClient() as client:
        if q["shape"] == "nouls":
            fn = lambda r: jev_nouls_one(client, r, q, state_fn)
        else:
            def fn(r):
                rec = test1.jev_one(client, r, q["options"], q["instructions"], state_fn)
                if rec.get("confidence") is not None:
                    rec["keep"] = rec["confidence"] >= THRESHOLD
                return rec
        with cf.ThreadPoolExecutor(test1.WORKERS) as ex:
            return list(ex.map(fn, rows))


def retrieval_only(row, examples):
    count, summed = Counter(), defaultdict(float)
    for n in examples[row["id"]]:
        count[n["home"]] += 1
        summed[n["home"]] += n["score"]
    best = max(count, key=lambda h: (count[h], summed[h]))
    return {**test1.meta(row), "system": "retrieval", "model": "bm25-k10-majority",
            "served_model": "bm25-k10-majority (no model)", "predicted": best,
            "confidence": None, "keep": None, "votes": dict(count),
            "tie_broken_by_score": sum(1 for h in count if count[h] == count[best]) > 1,
            "cost_usd": 0.0, "cost_basis": "no model call"}


def questions_for(arm, path):
    if arm == "G":
        if not FROZEN.exists():
            sys.exit("data/test1c-questions.json is not frozen yet")
        return json.loads(FROZEN.read_text(encoding="utf-8"))
    if path:
        return json.loads(open(path, encoding="utf-8").read())
    return base_questions("nouls" if arm == "F" else "choice")


def run(set_name, arm, label, qpath):
    key_path, nbr_path = SETS[set_name]
    if set_name == "H" and arm != "C" and not FROZEN.exists():
        sys.exit("no model call on H until data/test1c-questions.json is frozen")
    rows = test1.load_rows(key_path)
    examples = {r["id"]: r["neighbours"] for r in test1.load_rows(nbr_path)}
    state_fn = make_state(examples)
    t0 = time.time()
    q = None
    if arm == "C":
        out = [retrieval_only(r, examples) for r in rows]
    elif arm == "D":
        out = test1.run_llm(rows, test1.ROUTING_OPTIONS, test1b.INSTRUCTIONS, state_fn)
        for r in out:
            if r.get("confidence") is not None:
                r["keep"] = r["confidence"] >= THRESHOLD
    else:
        q = questions_for(arm, qpath)
        out = run_jev(rows, q, state_fn)
    RESULTS.mkdir(exist_ok=True)
    prefix = "test1c-W-" if set_name == "W" else "test1c-"
    dest = RESULTS / f"{prefix}{arm}-{label}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with open(dest, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps({**r, "task": "routing", "set": set_name, "arm": arm,
                                 "run": label, "question_shape": q["shape"] if q else None,
                                 "questions_file": qpath or (str(FROZEN.name) if arm == "G"
                                                            else None)},
                                ensure_ascii=False) + "\n")
    errs = sum(1 for r in out if r.get("error") or not r.get("predicted"))
    right = sum(1 for r in out if r.get("predicted") == r["label"])
    print(f"wrote {dest.relative_to(HERE)}  {len(out)} rows, {errs} unusable, "
          f"{right}/{len(out)} agree, {time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--set", choices=list(SETS), required=True)
    r.add_argument("--arm", choices=["B", "C", "D", "F", "G"], required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--questions", help="question-set JSON (W rounds only)")
    args = ap.parse_args()
    if args.set == "H" and args.questions:
        sys.exit("H arms use the baseline set or, for G, the frozen file only")
    test1.load_env()
    run(args.set, args.arm, args.label, args.questions)


if __name__ == "__main__":
    main()
