#!/usr/bin/env python3
"""Score Test 1c exactly as test1c-preregistration.md says, from the raw runs only.

    python3 analyse1c.py    # validates every held-out run file, prints and writes
                            # results/test1c-summary.json

Held-out arms: results/test1c-{B,C,D,F,G}-r*.jsonl (75 notes). The working-set rounds
(results/test1c-W-*) are reported as description only. Majority answers and the exact McNemar
test are analyse.py's. Keeping or passing on uses each row's `keep` field, which test1c.py sets by
the pre-registered rule (Choice: confidence >= 0.80; Nouls: top >= 0.80 and second < 0.50).
Exits 1 if any run file is invalid. Standard library only.
"""

import json
import math
import sys
from collections import Counter, defaultdict

import analyse

RESULTS = analyse.RESULTS
DATA = RESULTS.parent / "data"
ALPHA = 0.05
N_EXPECTED = 75
ARMS = {
    "C": ("Retrieval only (BM25 k=10 majority)", 1, None),
    "B": ("Jev, one Choice, Test 1b wording", 5, "jev-1.13.0"),
    "D": ("Sonnet 5, Test 1b wording", 5, "anthropic/claude-sonnet-5"),
    "F": ("Jev, one yes/no per home, Test 1b wording", 5, "jev-1.13.0"),
    "G": ("Jev, reworded (frozen test1c-questions.json)", 5, "jev-1.13.0"),
}


def load(arm):
    runs, problems = {}, []
    served = ARMS[arm][2]
    for p in sorted(RESULTS.glob(f"test1c-{arm}-r*.jsonl")):
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        if len(rows) != N_EXPECTED:
            problems.append(f"{p.name}: {len(rows)} rows, expected {N_EXPECTED}")
        for r in rows:
            if r.get("error") or not r.get("predicted"):
                problems.append(f"{p.name} {r['id']}: no usable answer")
            if not r.get("served_model"):
                problems.append(f"{p.name} {r['id']}: served model not logged")
            elif served and r["served_model"] != served:
                problems.append(f"{p.name} {r['id']}: served {r['served_model']}")
        runs[rows[0]["run"]] = {r["id"]: r for r in rows}
    if len(runs) != ARMS[arm][1]:
        problems.append(f"arm {arm}: {len(runs)} runs, expected {ARMS[arm][1]}")
    return runs, problems


def majority_right(runs):
    maj, labels = analyse.majority({k: list(v.values()) for k, v in runs.items()})
    return sorted(i for i, a in maj.items() if a == labels[i]), maj


def arm_report(arm, runs):
    rows = [r for run in runs.values() for r in run.values()]
    right, _ = majority_right(runs)
    per_run = [sum(analyse.right(r) for r in run.values()) / N_EXPECTED
               for _, run in sorted(runs.items())]
    by_id = defaultdict(set)
    for r in rows:
        by_id[r["id"]].add(r["predicted"])
    confusion = defaultdict(Counter)
    for r in rows:
        confusion[r["label"]][r["predicted"]] += 1
    rep = {"arm": arm, "description": ARMS[arm][0], "runs": len(runs), "calls": len(rows),
           "agreement_per_run": per_run, "agreement_mean": sum(per_run) / len(per_run),
           "agreement_min": min(per_run), "agreement_max": max(per_run),
           "majority_agreement": len(right) / N_EXPECTED, "majority_right": right,
           "items_answer_changed": sum(1 for s in by_id.values() if len(s) > 1),
           "cost_per_item_usd": sum(r["cost_usd"] for r in rows) / len(rows),
           "cost_total_usd": sum(r["cost_usd"] for r in rows),
           "confusion": {k: dict(v) for k, v in confusion.items()}}
    if arm != "C":
        kept = [r for r in rows if r.get("keep")]
        wrong = [r for r in kept if not analyse.right(r)]
        rep.update({"kept_answers": len(kept), "kept_wrong": len(wrong),
                    "kept_error_rate": len(wrong) / len(kept) if kept else None,
                    "passed_on_share": 1 - len(kept) / len(rows),
                    "kept_wrong_ids": sorted({r["id"] for r in wrong})})
    return rep


def cascade(jev_runs, d_runs):
    """Jev -> Claude: Jev's answer where kept, D's otherwise; run i paired with D's run i."""
    names_j, names_d = sorted(jev_runs), sorted(d_runs)
    out, cost, passed = {}, 0.0, 0
    for nj, nd in zip(names_j, names_d):
        run = {}
        for i, j in jev_runs[nj].items():
            d = d_runs[nd][i]
            if j.get("keep"):
                run[i] = {**j}
                cost += j["cost_usd"]
            else:
                run[i] = {**j, "predicted": d["predicted"]}
                cost += j["cost_usd"] + d["cost_usd"]
                passed += 1
        out[nj] = run
    calls = len(names_j) * N_EXPECTED
    right, _ = majority_right(out)
    per_run = [sum(analyse.right(r) for r in run.values()) / N_EXPECTED
               for _, run in sorted(out.items())]
    return out, {"majority_agreement": len(right) / N_EXPECTED, "majority_right": right,
                 "agreement_mean": sum(per_run) / len(per_run), "agreement_per_run": per_run,
                 "passed_to_claude_share": passed / calls, "cost_per_item_usd": cost / calls,
                 "pairing": [f"{a}+{b}" for a, b in zip(names_j, names_d)]}


def compare(name_x, name_y, rx, ry):
    xr, yr = set(rx), set(ry)
    b, c = len(xr - yr), len(yr - xr)
    diff = (b - c) / N_EXPECTED
    se = math.sqrt(max((b + c) / N_EXPECTED - diff ** 2, 0) / N_EXPECTED)
    return {"pair": f"{name_x} vs {name_y}", "items": N_EXPECTED,
            "first_right_second_wrong": b, "second_right_first_wrong": c,
            "mcnemar_exact_p": analyse.exact_mcnemar(b, c), "difference_points": 100 * diff,
            "wald_95_low": 100 * (diff - 1.96 * se), "wald_95_high": 100 * (diff + 1.96 * se)}


def holm(tests):
    order = sorted(range(len(tests)), key=lambda i: tests[i]["mcnemar_exact_p"])
    m, still = len(tests), True
    for rank, i in enumerate(order):
        t = tests[i]
        t["holm_threshold"] = ALPHA / (m - rank)
        still = still and t["mcnemar_exact_p"] < t["holm_threshold"]
        t["significant_after_holm"] = still
        t["first_better"] = still and t["first_right_second_wrong"] > t["second_right_first_wrong"]
        t["first_worse"] = still and t["first_right_second_wrong"] < t["second_right_first_wrong"]


def bar(rep):
    rate = rep["kept_error_rate"]
    if rate is None or rate > analyse.HIGH_CONF_ERROR_BAR:
        return "don't"
    return "use it" if rep["passed_on_share"] <= analyse.ESCALATION_BAR else "triage only"


def working_set():
    out = {}
    for p in sorted(RESULTS.glob("test1c-W-*.jsonl")):
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        out[p.name] = {"agree": sum(analyse.right(r) for r in rows), "items": len(rows),
                       "questions_file": rows[0].get("questions_file"),
                       "shape": rows[0].get("question_shape")}
    return out


def main():
    runs, reps, problems = {}, {}, []
    for arm in ARMS:
        runs[arm], probs = load(arm)
        problems += probs
    if problems:
        print("INVALID RUN FILES:")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    for arm in ARMS:
        reps[arm] = arm_report(arm, runs[arm])

    casc = {}
    for arm in ("B", "F", "G"):
        _, casc[arm] = cascade(runs[arm], runs["D"])

    tests = [
        compare("Jev->Claude (B)", "D", casc["B"]["majority_right"], reps["D"]["majority_right"]),
        compare("F", "B", reps["F"]["majority_right"], reps["B"]["majority_right"]),
        compare("G", "B", reps["G"]["majority_right"], reps["B"]["majority_right"]),
        compare("B", "C", reps["B"]["majority_right"], reps["C"]["majority_right"]),
    ]
    holm(tests)
    esc, shape, reword, repl = tests
    cost_ok = casc["B"]["cost_per_item_usd"] <= 0.5 * reps["D"]["cost_per_item_usd"]
    verdict = {
        "escalation": ("Escalation pays" if not esc["first_worse"] and cost_ok
                       else "Escalation does not pay"),
        "escalation_cost_ratio_to_D": casc["B"]["cost_per_item_usd"] / reps["D"]["cost_per_item_usd"],
        "question_shape": ("Narrow questions help" if shape["first_better"] else
                           "Narrow questions hurt" if shape["first_worse"] else
                           "No difference shown"),
        "rewording": "Rewording carried over" if reword["first_better"] else
                     "Rewording did not carry over",
        "replication": ("Retrieval did the work again" if not repl["first_better"]
                        else "Jev beat retrieval"),
        "test1_bar_jev_to_me": {a: bar(reps[a]) for a in ("B", "F", "G")},
    }
    nbrs = [json.loads(l) for l in open(DATA / "test1c-neighbours.jsonl", encoding="utf-8")]
    out = {"test": "1c", "preregistration": "test1c-preregistration.md",
           "keep_line": 0.80, "second_bar_nouls": 0.50,
           "arms": reps, "escalation_jev_to_claude": casc, "comparisons_holm": tests,
           "verdict": verdict, "working_set_rounds_description_only": working_set(),
           "near_duplicate_ids": sorted(r["id"] for r in nbrs
                                        if any(n["near_duplicate"] for n in r["neighbours"]))}
    (RESULTS / "test1c-summary.json").write_text(json.dumps(out, indent=2) + "\n",
                                                  encoding="utf-8")
    print(json.dumps({"verdict": verdict, "comparisons": tests}, indent=2))
    for a, r in reps.items():
        extra = "" if a == "C" else (f" kept-wrong {r['kept_wrong']}/{r['kept_answers']} "
                                     f"({r['kept_error_rate']:.3f}) passed {r['passed_on_share']:.3f}")
        print(f"{a}: majority {r['majority_agreement']:.3f} mean {r['agreement_mean']:.3f} "
              f"[{r['agreement_min']:.3f}-{r['agreement_max']:.3f}] cost {r['cost_per_item_usd']:.6f} "
              f"changed {r['items_answer_changed']}{extra}")
    for a, c in casc.items():
        print(f"Jev({a})->Claude: majority {c['majority_agreement']:.3f} mean {c['agreement_mean']:.3f} "
              f"passed {c['passed_to_claude_share']:.3f} cost {c['cost_per_item_usd']:.6f}")


if __name__ == "__main__":
    main()
