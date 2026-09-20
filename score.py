#!/usr/bin/env python3
"""Score one or more benchmark runs against the rule pre-registered in README.md.

    python3 score.py results/jev-20260920-113000.jsonl results/llm-20260920-113000.jsonl

Reports, per run: accuracy overall and per tier, a confusion matrix, precision and recall
per class, a reliability table with expected calibration error, and measured cost and
latency per claim. Then it applies the decision rule and says pass or fail on each clause.

Prices come from prices.json. If a price is missing the cost lines say UNPRICED rather
than guessing: a made-up price is worse than no price.
"""

import json
import pathlib
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
CLASSES = ["supported", "unsupported", "not_addressed"]
GATE_CLASS = "unsupported"          # the class the gate exists to catch
RECALL_FLOOR = 0.80
PRECISION_FLOOR = 0.60
RECALL_NO = 0.60


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def prices():
    path = HERE / "prices.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def confusion(rows):
    m = defaultdict(Counter)
    for r in rows:
        m[r["label"]][r.get("predicted")] += 1
    return m


def prf(rows, cls):
    tp = sum(1 for r in rows if r["label"] == cls and r.get("predicted") == cls)
    fp = sum(1 for r in rows if r["label"] != cls and r.get("predicted") == cls)
    fn = sum(1 for r in rows if r["label"] == cls and r.get("predicted") != cls)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return prec, rec, tp, fp, fn


def reliability(rows, bins=5):
    """Bucket by stated confidence and report how often each bucket was right."""
    scored = [r for r in rows if r.get("confidence") is not None and r.get("predicted")]
    if not scored:
        return [], None
    edges = [i / bins for i in range(bins + 1)]
    table, ece, n = [], 0.0, len(scored)
    for lo, hi in zip(edges, edges[1:]):
        chunk = [r for r in scored
                 if (r["confidence"] >= lo and (r["confidence"] < hi or hi == 1.0))]
        if not chunk:
            continue
        acc = sum(1 for r in chunk if r["predicted"] == r["label"]) / len(chunk)
        mean_conf = sum(r["confidence"] for r in chunk) / len(chunk)
        table.append((lo, hi, len(chunk), mean_conf, acc))
        ece += (len(chunk) / n) * abs(mean_conf - acc)
    return table, ece


def cost_per_claim(rows, price_book):
    system = rows[0].get("system")
    model = rows[0].get("model")
    key = f"{system}:{model}"
    # OpenRouter reports what it actually charged. A measured charge beats a price table.
    charged = [r["charged_usd"] for r in rows if r.get("charged_usd") is not None]
    if charged and len(charged) == len(rows):
        return sum(charged) / len(charged), key + " (charged)"
    p = price_book.get(key) or price_book.get(system)
    if not p:
        return None, key
    tin = sum(r.get("input_tokens", 0) for r in rows)
    tout = sum(r.get("output_tokens", 0) for r in rows)
    total = (tin / 1e6) * p["input_per_mtok"] + (tout / 1e6) * p["output_per_mtok"]
    return total / len(rows), key


def pct(x):
    return "   n/a" if x is None else f"{x * 100:5.1f}%"


def report(path, price_book):
    rows = load(path)
    errors = [r for r in rows if r.get("error")]
    unparsed = [r for r in rows if not r.get("error") and not r.get("predicted")]
    ok = [r for r in rows if r.get("predicted")]

    print("=" * 72)
    print(f"{path.name}   system={rows[0].get('system')}  model={rows[0].get('model')}")
    print("=" * 72)
    if errors:
        print(f"!! {len(errors)} call(s) failed outright")
    if unparsed:
        print(f"!! {len(unparsed)} reply/replies produced no usable verdict "
              f"(counted as wrong, which is what they are in a gate)")

    graded = ok + unparsed
    acc = sum(1 for r in graded if r.get("predicted") == r["label"]) / len(graded)
    print(f"\nAccuracy, all graded ({len(graded)}): {pct(acc)}")
    for tier in ("A", "B"):
        sub = [r for r in graded if r.get("tier") == tier]
        if sub:
            a = sum(1 for r in sub if r.get("predicted") == r["label"]) / len(sub)
            name = "real, adversarial" if tier == "A" else "constructed controls"
            print(f"  tier {tier} ({name}, n={len(sub)}): {pct(a)}")

    print("\nConfusion (rows = true label, columns = predicted)")
    m = confusion(graded)
    print(f"{'':<16}" + "".join(f"{c:>16}" for c in CLASSES) + f"{'none':>8}")
    for cls in CLASSES:
        row = m.get(cls, Counter())
        print(f"{cls:<16}" + "".join(f"{row.get(c, 0):>16}" for c in CLASSES)
              + f"{row.get(None, 0):>8}")

    print("\nPer class")
    for cls in CLASSES:
        prec, rec, tp, fp, fn = prf(graded, cls)
        mark = "  <- the gate's job" if cls == GATE_CLASS else ""
        print(f"  {cls:<16} precision {pct(prec)}  recall {pct(rec)}"
              f"   (tp {tp}, fp {fp}, fn {fn}){mark}")

    table, ece = reliability(graded)
    print("\nCalibration: does stated confidence track being right")
    if not table:
        print("  no usable confidences returned")
    else:
        print(f"  {'bucket':<14}{'n':>5}{'mean conf':>12}{'actual':>10}")
        for lo, hi, n, mc, a in table:
            print(f"  {f'{lo:.1f}-{hi:.1f}':<14}{n:>5}{mc:>11.2f}{pct(a):>11}")
        print(f"  expected calibration error: {ece:.3f}  (0 is perfect, lower is better)")

    lat = sum(r.get("seconds", 0) for r in ok) / len(ok) if ok else None
    print(f"\nLatency per claim: {lat:.2f}s" if lat else "\nLatency per claim: n/a")
    cpc, key = cost_per_claim(ok or rows, price_book)
    if cpc is None:
        print(f"Cost per claim:    UNPRICED (no entry '{key}' in prices.json)")
    else:
        print(f"Cost per claim:    ${cpc:.6f}")

    prec, rec, *_ = prf(graded, GATE_CLASS)
    return {"path": path, "system": rows[0].get("system"), "acc": acc,
            "precision": prec, "recall": rec, "ece": ece, "latency": lat, "cost": cpc}


def verdict(runs):
    jev = next((r for r in runs if r["system"] == "jev"), None)
    llm = next((r for r in runs if r["system"] == "llm"), None)
    if not jev:
        return
    print("\n" + "=" * 72)
    print("THE RULE, as written before the first run")
    print("=" * 72)

    def line(ok, text):
        print(f"  [{'PASS' if ok else 'FAIL' if ok is False else ' ?? '}] {text}")

    r, p = jev["recall"], jev["precision"]
    line(None if r is None else r >= RECALL_FLOOR,
         f"recall on unsupported >= {RECALL_FLOOR:.2f}   (Jev {pct(r).strip()})")
    if llm:
        line(None if r is None or llm["recall"] is None else r >= llm["recall"],
             f"and at least the LLM's         (LLM {pct(llm['recall']).strip()})")
    line(None if p is None else p >= PRECISION_FLOOR,
         f"precision on unsupported >= {PRECISION_FLOOR:.2f} (Jev {pct(p).strip()})")
    if llm and jev["cost"] is not None and llm["cost"] is not None:
        line(jev["cost"] < llm["cost"],
             f"cheaper per claim              (${jev['cost']:.6f} vs ${llm['cost']:.6f})")
    else:
        line(None, "cheaper per claim              (needs prices.json)")
    if llm and jev["latency"] and llm["latency"]:
        line(jev["latency"] < llm["latency"],
             f"faster per claim               ({jev['latency']:.2f}s vs {llm['latency']:.2f}s)")

    if r is not None and r < RECALL_NO:
        print(f"\n  => recall on unsupported is below {RECALL_NO:.2f}. By the rule, that is a no.")
    print("\n  Calibration clause is a judgement on the reliability table above, not a "
          "threshold:\n  are high-confidence items right materially more often than "
          "low-confidence ones?")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    book = prices()
    runs = [report(pathlib.Path(p), book) for p in sys.argv[1:]]
    verdict(runs)


if __name__ == "__main__":
    main()
