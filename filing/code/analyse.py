#!/usr/bin/env python3
"""Score Test 1 exactly as test1-preregistration.md says. Written before the first run.

    python3 analyse.py routing      # prints the report and writes results/<task>-summary.json
    python3 analyse.py ideas

Reads every results/<task>-<system>-r*.jsonl. Standard library only.
"""

import json
import math
import pathlib
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
THRESHOLD = 0.80          # fixed in the pre-registration
HIGH_CONF_ERROR_BAR = 0.05
ESCALATION_BAR = 0.50
SYSTEMS = ("jev", "llm")


def load_runs(task, system):
    runs = {}
    for p in sorted(RESULTS.glob(f"{task}-{system}-r*.jsonl")):
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        runs[rows[0]["run"]] = rows
    return runs


def right(r):
    return bool(r.get("predicted")) and r["predicted"] == r["label"]


def exact_mcnemar(b, c):
    """Two-sided exact binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def majority(runs):
    """id -> the answer given in at least 3 of the 5 runs, or None."""
    by_id = defaultdict(list)
    labels = {}
    for rows in runs.values():
        for r in rows:
            by_id[r["id"]].append(r.get("predicted"))
            labels[r["id"]] = r["label"]
    need = len(runs) // 2 + 1
    out = {}
    for i, answers in by_id.items():
        ans, n = Counter(answers).most_common(1)[0]
        out[i] = ans if n >= need else None
    return out, labels


def system_report(task, system, runs):
    per_run = []
    pooled = [r for rows in runs.values() for r in rows]
    for name, rows in sorted(runs.items()):
        n = len(rows)
        conf = [r for r in rows if r.get("confidence") is not None and r.get("predicted")]
        high = [r for r in conf if r["confidence"] >= THRESHOLD]
        per_run.append({
            "run": name,
            "items": n,
            "agreement": sum(map(right, rows)) / n,
            "unusable": sum(1 for r in rows if not r.get("predicted")),
            "escalated_share": 1 - len(high) / n,
            "high_conf_answers": len(high),
            "high_conf_errors": sum(1 for r in high if not right(r)),
            "served_models": sorted({str(r.get("served_model")) for r in rows}),
        })
    high = [r for r in pooled if r.get("predicted") and r.get("confidence") is not None
            and r["confidence"] >= THRESHOLD]
    hc_err = sum(1 for r in high if not right(r))
    costs = [r["cost_usd"] for r in pooled if r.get("cost_usd") is not None]
    maj, labels = majority(runs)
    changed = 0
    by_id = defaultdict(set)
    for r in pooled:
        by_id[r["id"]].add(r.get("predicted"))
    changed = sum(1 for s in by_id.values() if len(s) > 1)
    confusion = defaultdict(Counter)
    for r in pooled:
        confusion[r["label"]][r.get("predicted") or "none"] += 1
    agreements = [p["agreement"] for p in per_run]
    return {
        "system": system,
        "runs": len(runs),
        "per_run": per_run,
        "agreement_mean": sum(agreements) / len(agreements),
        "agreement_min": min(agreements),
        "agreement_max": max(agreements),
        "majority_agreement": sum(1 for i, a in maj.items() if a == labels[i]) / len(maj),
        "majority_right": sorted(i for i, a in maj.items() if a == labels[i]),
        "escalated_share_pooled": 1 - len(high) / len(pooled),
        "high_conf_answers_pooled": len(high),
        "high_conf_errors_pooled": hc_err,
        "high_conf_error_rate": hc_err / len(high) if high else None,
        "high_conf_error_ids": sorted({r["id"] for r in high if not right(r)}),
        "cost_per_item_usd": sum(costs) / len(costs) if costs else None,
        "cost_calls_priced": len(costs),
        "calls": len(pooled),
        "items_answer_changed": changed,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "confidence_values": sorted(Counter(round(r["confidence"], 2) for r in pooled
                                            if r.get("confidence") is not None).items()),
    }


def verdict_for(rep, other=None, sig_worse=False):
    rate = rep["high_conf_error_rate"]
    if rate is None or rate > HIGH_CONF_ERROR_BAR:
        return "don't"
    cheaper = other is None or (rep["cost_per_item_usd"] or 0) < (other["cost_per_item_usd"] or 0)
    if rep["escalated_share_pooled"] <= ESCALATION_BAR and not sig_worse and cheaper:
        return "use it"
    return "triage only"


def main():
    task = sys.argv[1]
    reps = {}
    for s in SYSTEMS:
        runs = load_runs(task, s)
        if runs:
            reps[s] = system_report(task, s, runs)
    out = {"task": task, "threshold": THRESHOLD, "systems": reps}
    if len(reps) == 2:
        j, l = reps["jev"], reps["llm"]
        jr, lr = set(j["majority_right"]), set(l["majority_right"])
        ids = {r["id"] for rows in load_runs(task, "jev").values() for r in rows}
        b = len((jr - lr) & ids)   # Jev right, Claude wrong
        c = len((lr - jr) & ids)   # Claude right, Jev wrong
        p = exact_mcnemar(b, c)
        n = len(ids)
        diff = (b - c) / n
        se = math.sqrt(max((b + c) / n - diff ** 2, 0) / n)
        if p < 0.05:
            outcome = "Jev wins" if b > c else "Jev loses"
        else:
            outcome = "can't tell them apart"
        out["comparison"] = {
            "items": n, "jev_right_llm_wrong": b, "llm_right_jev_wrong": c,
            "mcnemar_exact_p": p, "difference_points": 100 * diff,
            "wald_95_low": 100 * (diff - 1.96 * se), "wald_95_high": 100 * (diff + 1.96 * se),
            "outcome": outcome,
        }
        jev_sig_worse = p < 0.05 and c > b
        out["verdict_jev"] = verdict_for(j, l, sig_worse=jev_sig_worse)
        out["same_bar_llm"] = verdict_for(l)
    dest = RESULTS / f"{task}-summary.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
