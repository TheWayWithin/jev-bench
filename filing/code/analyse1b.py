#!/usr/bin/env python3
"""Score Test 1b exactly as test1b-preregistration.md says, from the raw runs only.

    python3 analyse1b.py     # validates every run file, prints and writes
                             # results/test1b-summary.json

Arms A and E are Test 1's runs (results/routing-{jev,llm}-r*.jsonl); B, C and D are
results/test1b-{B,C,D}-r*.jsonl. The per-arm metrics are analyse.py's system_report, the
McNemar test is analyse.py's exact_mcnemar, and Test 1's bar is analyse.py's verdict_for,
so nothing is re-implemented. Standard library only. Exits 1 if any run file is invalid.
"""

import json
import math
import sys
from collections import Counter

import analyse
import test1b_neighbours as nb

RESULTS = analyse.RESULTS
ALPHA = 0.05
ARMS = {
    "A": ("Jev, no examples", "routing-jev-r*.jsonl", "jev-1.13.0"),
    "B": ("Jev with the 10 examples", "test1b-B-r*.jsonl", "jev-1.13.0"),
    "C": ("Retrieval only (BM25 k=10 majority)", "test1b-C-r*.jsonl", None),
    "D": ("Sonnet 5 with the 10 examples", "test1b-D-r*.jsonl", "anthropic/claude-sonnet-5"),
    "E": ("Sonnet 5, no examples", "routing-llm-r*.jsonl", "anthropic/claude-sonnet-5"),
}
EXPECTED_RUNS = {"A": 5, "B": 5, "C": 1, "D": 5, "E": 5}


def load_arm(arm):
    runs, problems = {}, []
    _, pattern, served = ARMS[arm]
    for p in sorted(RESULTS.glob(pattern)):
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        if len(rows) != 83:
            problems.append(f"{p.name}: {len(rows)} rows, expected 83")
        if len({r["id"] for r in rows}) != len(rows):
            problems.append(f"{p.name}: duplicate ids")
        for r in rows:
            if r.get("error") or not r.get("predicted"):
                problems.append(f"{p.name} {r['id']}: no usable answer")
            if not r.get("served_model"):
                problems.append(f"{p.name} {r['id']}: served model not logged")
            elif served and r["served_model"] != served:
                problems.append(f"{p.name} {r['id']}: served {r['served_model']}")
        runs[rows[0]["run"]] = rows
    if len(runs) != EXPECTED_RUNS[arm]:
        problems.append(f"arm {arm}: {len(runs)} runs, expected {EXPECTED_RUNS[arm]}")
    return runs, problems


def compare(x, y, rx, ry, ids, restrict=None):
    """Exact McNemar on majority answers; b = x right and y wrong, c = y right and x wrong."""
    ids = set(ids) if restrict is None else set(ids) - set(restrict)
    xr, yr = set(rx["majority_right"]) & ids, set(ry["majority_right"]) & ids
    b, c = len(xr - yr), len(yr - xr)
    n = len(ids)
    p = analyse.exact_mcnemar(b, c)
    diff = (b - c) / n
    se = math.sqrt(max((b + c) / n - diff ** 2, 0) / n)
    return {"pair": f"{x} vs {y}", "items": n, f"{x}_right_{y}_wrong": b,
            f"{y}_right_{x}_wrong": c, "mcnemar_exact_p": p,
            "difference_points": 100 * diff, "wald_95_low": 100 * (diff - 1.96 * se),
            "wald_95_high": 100 * (diff + 1.96 * se),
            f"{x}_significantly_better": p < ALPHA and b > c,
            f"{x}_significantly_worse": p < ALPHA and c > b}


def main():
    reps, problems, runs_by_arm = {}, [], {}
    for arm in ARMS:
        runs, probs = load_arm(arm)
        problems += probs
        runs_by_arm[arm] = runs
        if runs:
            rep = analyse.system_report("routing", arm, runs)
            rep["arm"], rep["description"] = arm, ARMS[arm][0]
            rep["run_files"] = sorted(p.name for p in RESULTS.glob(ARMS[arm][1]))
            costs = [r["cost_usd"] for rows in runs.values() for r in rows
                     if r.get("cost_usd") is not None]
            rep["cost_total_usd"] = sum(costs)
            conf1 = [r for rows in runs.values() for r in rows if r.get("confidence") == 1.0]
            rep["answers_at_confidence_1"] = len(conf1)
            rep["wrong_at_confidence_1"] = sum(1 for r in conf1 if not analyse.right(r))
            if arm == "C":  # no confidence, so no escalation or confident-error figure
                for k in ("escalated_share_pooled", "high_conf_answers_pooled",
                          "high_conf_errors_pooled", "high_conf_error_rate"):
                    rep[k] = None
                rep["high_conf_error_ids"] = []
                rep["answers_at_confidence_1"] = rep["wrong_at_confidence_1"] = None
                rep["ties_broken_by_score"] = sum(1 for rows in runs.values() for r in rows
                                                 if r.get("tie_broken_by_score"))
            reps[arm] = rep
    if problems:
        print("INVALID RUN FILES:")
        for p in problems:
            print("  " + p)
        sys.exit(1)

    ids = sorted({r["id"] for r in runs_by_arm["A"]["r1"]})
    neighbours = nb.load(nb.NEIGHBOURS)
    dup_ids = sorted(r["id"] for r in neighbours
                     if any(n["near_duplicate"] for n in r["neighbours"]))

    main_cmp = compare("B", "C", reps["B"], reps["C"], ids)
    second = compare("B", "D", reps["B"], reps["D"], ids)
    reported = [compare("B", "A", reps["B"], reps["A"], ids),
                compare("D", "E", reps["D"], reps["E"], ids),
                compare("C", "A", reps["C"], reps["A"], ids)]
    sensitivity = [compare("B", "C", reps["B"], reps["C"], ids, restrict=dup_ids),
                   compare("B", "D", reps["B"], reps["D"], ids, restrict=dup_ids)]

    b_beats_c = main_cmp["B_significantly_better"]
    b_worse_d = second["B_significantly_worse"]
    held = []
    if b_beats_c and not b_worse_d:
        held.append("Jev with examples earns its place")
    if not b_beats_c:
        held.append("The retrieval did the work")
    if b_worse_d:
        held.append("Jev still loses with examples")

    d_worse_b = second["D_right_B_wrong"] < second["B_right_D_wrong"] and \
        second["mcnemar_exact_p"] < ALPHA
    out = {
        "test": "1b",
        "preregistration": "test1b-preregistration.md",
        "threshold": analyse.THRESHOLD,
        "confident_error_bar": analyse.HIGH_CONF_ERROR_BAR,
        "escalation_bar": analyse.ESCALATION_BAR,
        "neighbours": {"file": "data/test1b-neighbours.jsonl",
                       "sha256": nb.sha(nb.NEIGHBOURS), "pool_file": "data/test1b-pool.jsonl",
                       "pool_notes": len(nb.load(nb.POOL)), "pool_sha256": nb.sha(nb.POOL),
                       "k": nb.K, "near_duplicate_jaccard": nb.NEAR_DUP_JACCARD,
                       "test_notes_with_near_duplicate_neighbour": len(dup_ids),
                       "near_duplicate_ids": dup_ids,
                       "neighbour_homes_matching_label": sum(
                           1 for r in neighbours for n in r["neighbours"]
                           if n["home"] == r["label"]),
                       "neighbour_slots": sum(len(r["neighbours"]) for r in neighbours)},
        "arms": reps,
        "main_comparison": main_cmp,
        "second_comparison": second,
        "reported_not_tested": reported,
        "descriptive_without_near_duplicates": sensitivity,
        "verdict_rule_held": held,
        "test1_bar": {
            "B": analyse.verdict_for(reps["B"], reps["D"], sig_worse=b_worse_d),
            "D": analyse.verdict_for(reps["D"], reps["B"], sig_worse=d_worse_b),
            "D_without_cheaper_clause": analyse.verdict_for(reps["D"]),
        },
        "near_duplicate_items_by_arm": {
            arm: {i: i in reps[arm]["majority_right"] for i in dup_ids} for arm in reps},
    }
    dest = RESULTS / "test1b-summary.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("main_comparison", "second_comparison",
                                            "reported_not_tested", "verdict_rule_held",
                                            "test1_bar")}, indent=2))
    for arm, r in reps.items():
        print(f"{arm} {r['description']}: mean {r['agreement_mean']:.3f} "
              f"[{r['agreement_min']:.3f}-{r['agreement_max']:.3f}] "
              f"majority {r['majority_agreement']:.3f} esc {r['escalated_share_pooled']} "
              f"hce {r['high_conf_errors_pooled']}/{r['high_conf_answers_pooled']} "
              f"cost/item {r['cost_per_item_usd']} total {r['cost_total_usd']:.4f} "
              f"changed {r['items_answer_changed']}")


if __name__ == "__main__":
    main()
