#!/usr/bin/env python3
"""Descriptive extras for Test 1, allowed by the pre-registration as description only:
accuracy at each model's own confidence values (never used to move the 0.80 line), and
the confident errors item by item. Written after the runs; it changes no verdict.

    python3 describe.py routing   # writes results/routing-descriptive.json
"""

import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
DATA = HERE / "data"


def main():
    task = sys.argv[1]
    key = {json.loads(l)["id"]: json.loads(l) for l in open(DATA / f"{task}-key.jsonl")}
    out = {"task": task, "note": "descriptive only; the verdict is analyse.py's"}
    for system in ("jev", "llm"):
        rows = [json.loads(l) for p in sorted(RESULTS.glob(f"{task}-{system}-r*.jsonl"))
                for l in open(p, encoding="utf-8") if l.strip()]
        n = len(rows)
        cuts = sorted({round(r["confidence"], 2) for r in rows}, reverse=True)
        curve = []
        for c in cuts:
            kept = [r for r in rows if r["confidence"] >= c]
            wrong = sum(1 for r in kept if r["predicted"] != r["label"])
            curve.append({"at_or_above": c, "coverage": len(kept) / n, "answers": len(kept),
                          "wrong": wrong, "error_rate": wrong / len(kept)})
        errs = Counter((r["id"], r["predicted"]) for r in rows
                       if r["confidence"] >= 0.80 and r["predicted"] != r["label"])
        out[system] = {
            "calls": n,
            "zero_error_top": max((p for p in curve if p["wrong"] == 0),
                                  key=lambda p: p["coverage"], default=None),
            "curve": curve,
            "confident_errors": [
                {"id": i, "title": key[i]["title"], "path": key[i]["path"],
                 "label": key[i]["label"], "answer": a, "runs": k}
                for (i, a), k in sorted(errs.items())],
        }
    dest = RESULTS / f"{task}-descriptive.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for s in ("jev", "llm"):
        print(s, "zero-error top:", out[s]["zero_error_top"])
        for p in out[s]["curve"]:
            if p["at_or_above"] in (1.0, 0.99, 0.98, 0.95, 0.9, 0.85, 0.8):
                print(f"  >= {p['at_or_above']}: coverage {p['coverage']:.3f} "
                      f"({p['answers']}), wrong {p['wrong']}, error {p['error_rate']:.3f}")
        for e in out[s]["confident_errors"]:
            print(f"  {e['id']} {e['label']} -> {e['answer']} x{e['runs']}  {e['path']}")


if __name__ == "__main__":
    main()
