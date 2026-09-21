#!/usr/bin/env python3
"""Risk and coverage: how much checking can you safely stop doing.

    python3 risk_coverage.py results/jev-*.jsonl results/llm-openai-gpt-5.4-*.jsonl ...

`score.py` answers "is it accurate". This answers the question a production engineer
actually has: if I auto-accept every verdict at or above confidence t and send the rest
to a person or a reasoning model, what fraction of the work goes away, and how often is
an accepted verdict wrong?

Three numbers per threshold, per run:

  coverage    share of claims whose stated confidence is >= t, so the pipeline keeps
              the verdict without escalating it
  error rate  share of THOSE that were wrong: the risk you are accepting
  escalated   1 - coverage, the share that still costs a person or a bigger model

Plus the one that matters most to a publishing gate specifically: **waved through**,
the count of claims accepted as `supported` at or above t whose true label was not
`supported`. Those are bad sentences going live with nobody looking at them.

Tier A (real, adversarial) and all 42 are reported separately. Tier A carries the
headline, exactly as in the README's decision rule.

A run with no usable confidences, or a threshold no item reaches, prints n/a rather
than a fabricated rate. Written 2026-09-21 for JevBench test 5.
"""

import argparse
import glob
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
THRESHOLDS = [0.95, 0.90, 0.85, 0.80, 0.70, 0.60]
ACCEPT_CLASS = "supported"   # the verdict that publishes a sentence with nobody looking


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def label_of(path, rows):
    """A readable name for the run: the model, not the filename."""
    model = rows[0].get("model") or "unknown"
    if rows[0].get("system") == "jev":
        return f"Jev ({model})"
    return model


def curve(rows, thresholds=THRESHOLDS):
    """One risk-coverage row per threshold. Unparsed replies count as wrong, which is
    what they are in a gate; an unparsed reply with no confidence cannot be accepted."""
    n = len(rows)
    out = []
    for t in thresholds:
        accepted = [r for r in rows
                    if r.get("confidence") is not None and r["confidence"] >= t]
        k = len(accepted)
        wrong = [r for r in accepted if r.get("predicted") != r["label"]]
        waved = [r for r in accepted
                 if r.get("predicted") == ACCEPT_CLASS and r["label"] != ACCEPT_CLASS]
        # The gate view. A claim is only published with nobody looking at it if the
        # verdict is `supported` AND the confidence cleared the bar. Everything else
        # reaches a human either way, so it is not a saving and not a risk.
        auto_pub = [r for r in accepted if r.get("predicted") == ACCEPT_CLASS]
        bad_total = sum(1 for r in rows if r["label"] != ACCEPT_CLASS)
        out.append({
            "threshold": t,
            "n": n,
            "accepted": k,
            "coverage": k / n if n else None,
            "errors": len(wrong),
            "error_rate": len(wrong) / k if k else None,
            "escalated": (n - k) / n if n else None,
            "waved_through": len(waved),
            "auto_published": len(auto_pub),
            "auto_published_share": len(auto_pub) / n if n else None,
            "bad_published_rate": len(waved) / len(auto_pub) if auto_pub else None,
            "escape_rate": len(waved) / bad_total if bad_total else None,
            "waved_ids": [r["id"] for r in waved],
        })
    return out


def pct(x, width=6):
    return f"{'n/a':>{width}}" if x is None else f"{x * 100:{width - 1}.1f}%"


def print_curve(name, rows, tier_name):
    print(f"\n{name}  —  {tier_name} (n={len(rows)})")
    conf = [r for r in rows if r.get("confidence") is not None]
    if not conf:
        print("  no usable confidences returned; risk-coverage is undefined for this run")
        return
    lo = min(r["confidence"] for r in conf)
    hi = max(r["confidence"] for r in conf)
    print(f"  stated confidence spans {lo:.2f} to {hi:.2f}")
    print(f"  {'thresh':>7}{'coverage':>11}{'accepted':>10}{'errors':>8}"
          f"{'err rate':>10}{'escalated':>11}{'waved':>7}")
    table = curve(rows)
    for row in table:
        print(f"  {row['threshold']:>7.2f}{pct(row['coverage'], 11)}"
              f"{row['accepted']:>10}{row['errors']:>8}"
              f"{pct(row['error_rate'], 10)}{pct(row['escalated'], 11)}"
              f"{row['waved_through']:>7}")

    bad_total = sum(1 for r in rows if r["label"] != ACCEPT_CLASS)
    print(f"  the gate view: of {len(rows)} claims, {bad_total} should not be published")
    print(f"  {'thresh':>7}{'auto-pub':>10}{'share':>8}{'bad pub':>9}"
          f"{'bad rate':>10}{'escaped':>9}   ids")
    for row in table:
        print(f"  {row['threshold']:>7.2f}{row['auto_published']:>10}"
              f"{pct(row['auto_published_share'], 8)}{row['waved_through']:>9}"
              f"{pct(row['bad_published_rate'], 10)}{pct(row['escape_rate'], 9)}"
              f"   {','.join(row['waved_ids']) or '-'}")


def knee(rows):
    """The lowest threshold at which the accepted set is still right >= 90% of the
    time, and how much coverage that buys. None if no threshold reaches it."""
    best = None
    for row in curve(rows):
        if row["error_rate"] is not None and row["error_rate"] <= 0.10:
            best = row
    return best


def cascade(cheap, dear, thresholds=THRESHOLDS):
    """Take the cheap model's verdict when it is confident, hand the rest to the dear
    one. The point of a calibrated confidence is that this beats either alone on the
    trade between accuracy and price, so compute it rather than assert it."""
    dear_by_id = {r["id"]: r for r in dear}
    pairs = [(c, dear_by_id[c["id"]]) for c in cheap if c["id"] in dear_by_id]
    cheap_cost = mean_cost(cheap)
    dear_cost = mean_cost(dear)
    out = []
    for t in thresholds:
        chosen = []
        escalated = 0
        for c, d in pairs:
            if c.get("confidence") is not None and c["confidence"] >= t:
                chosen.append((c["predicted"], c["label"], c["tier"]))
            else:
                escalated += 1
                chosen.append((d.get("predicted"), d["label"], d["tier"]))
        n = len(chosen)
        right = sum(1 for p, lab, _ in chosen if p == lab)
        a = [(p, lab) for p, lab, tier in chosen if tier == "A"]
        right_a = sum(1 for p, lab in a if p == lab)
        bad_pub = sum(1 for p, lab, _ in chosen
                      if p == ACCEPT_CLASS and lab != ACCEPT_CLASS)
        blended = None
        if cheap_cost is not None and dear_cost is not None:
            blended = cheap_cost + (escalated / n) * dear_cost if n else None
        out.append({
            "threshold": t, "n": n, "escalated": escalated,
            "escalated_share": escalated / n if n else None,
            "accuracy": right / n if n else None,
            "accuracy_tier_a": right_a / len(a) if a else None,
            "bad_published": bad_pub,
            "cost_per_claim": blended,
        })
    return out


def mean_cost(rows):
    """What this run actually cost per claim: the charge if the provider reported one,
    otherwise Jev's published input rate applied to the tokens it returned."""
    charged = [r["charged_usd"] for r in rows if r.get("charged_usd") is not None]
    if charged and len(charged) == len(rows):
        return sum(charged) / len(charged)
    book = {}
    path = HERE / "prices.json"
    if path.exists():
        book = json.loads(path.read_text(encoding="utf-8"))
    key = f"{rows[0].get('system')}:{rows[0].get('model')}"
    p = book.get(key) or book.get(rows[0].get("system"))
    if not p:
        return None
    tin = sum(r.get("input_tokens", 0) for r in rows)
    tout = sum(r.get("output_tokens", 0) for r in rows)
    return ((tin / 1e6) * p["input_per_mtok"]
            + (tout / 1e6) * p["output_per_mtok"]) / len(rows)


def print_cascade(cheap_name, dear_name, cheap, dear):
    print("\n" + "=" * 74)
    print(f"CASCADE — {cheap_name} when confident, {dear_name} for the rest")
    print("=" * 74)
    c_only = sum(1 for r in cheap if r.get("predicted") == r["label"]) / len(cheap)
    d_only = sum(1 for r in dear if r.get("predicted") == r["label"]) / len(dear)
    print(f"  for comparison: {cheap_name} alone {pct(c_only).strip()}, "
          f"{dear_name} alone {pct(d_only).strip()}, on all claims")
    print(f"  {'thresh':>7}{'escalated':>11}{'accuracy':>10}{'tier A':>9}"
          f"{'bad pub':>9}{'$/claim':>12}")
    for row in cascade(cheap, dear):
        cost = "n/a" if row["cost_per_claim"] is None else f"${row['cost_per_claim']:.6f}"
        print(f"  {row['threshold']:>7.2f}{pct(row['escalated_share'], 11)}"
              f"{pct(row['accuracy'], 10)}{pct(row['accuracy_tier_a'], 9)}"
              f"{row['bad_published']:>9}{cost:>12}")

    # Whether a cascade helps turns entirely on this: is the expensive model any good
    # on the claims the cheap one flagged as uncertain? Check it, do not assume it.
    dear_by_id = {r["id"]: r for r in dear}
    for t in (0.80,):
        sure = [c for c in cheap if (c.get("confidence") or 0) >= t]
        unsure = [c for c in cheap if (c.get("confidence") or 0) < t]
        for name, group in (("confident", sure), ("escalated", unsure)):
            for scope in ("all claims", "Tier A only"):
                g = group if scope == "all claims" else [r for r in group
                                                         if r.get("tier") == "A"]
                if not g:
                    continue
                d = [dear_by_id[c["id"]] for c in g if c["id"] in dear_by_id]
                c_acc = sum(1 for r in g if r["predicted"] == r["label"]) / len(g)
                d_acc = (sum(1 for r in d if r.get("predicted") == r["label"]) / len(d)
                         if d else None)
                print(f"  {name:>9} at {t:.2f}, {scope:<11} n={len(g):>2}: "
                      f"{cheap_name} {pct(c_acc).strip():>6}, "
                      f"{dear_name} {pct(d_acc).strip():>6}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*", help="result .jsonl files (globs are expanded)")
    ap.add_argument("--json", metavar="PATH", help="also write the full table as JSON")
    ap.add_argument("--cascade", nargs=2, metavar=("CHEAP", "DEAR"),
                    help="two result files: take CHEAP's verdict when it clears the "
                         "threshold, DEAR's otherwise, and price the result")
    args = ap.parse_args()

    paths = []
    for pattern in args.runs:
        hits = sorted(glob.glob(pattern))
        paths.extend(pathlib.Path(p) for p in (hits or [pattern]))
    if not paths and not args.cascade:
        sys.exit("give me at least one results/*.jsonl file")

    dump = []
    if paths:
        print("=" * 74)
        print("RISK AND COVERAGE — auto-accept at or above t, escalate the rest")
        print("=" * 74)
        print("coverage  = share of claims kept without escalation")
        print("err rate  = share of the kept ones whose verdict was wrong")
        print("waved     = kept as 'supported' when the true label was not: a bad")
        print("            sentence published with nobody looking at it")

    for path in paths:
        rows = load(path)
        graded = [r for r in rows if not r.get("error")]
        name = label_of(path, rows)
        tier_a = [r for r in graded if r.get("tier") == "A"]
        print("\n" + "-" * 74)
        print_curve(name, tier_a, "Tier A, real adversarial claims")
        print_curve(name, graded, "all claims")
        k = knee(tier_a)
        if k:
            print(f"  Tier A: highest-coverage threshold still at or under 10% error is "
                  f"{k['threshold']:.2f}, keeping {pct(k['coverage']).strip()} of claims")
        else:
            print("  Tier A: no threshold in the set holds error at or under 10%")
        dump.append({"file": path.name, "run": name,
                     "tier_a": curve(tier_a), "all": curve(graded)})

    if args.cascade:
        cheap_rows = [r for r in load(args.cascade[0]) if not r.get("error")]
        dear_rows = [r for r in load(args.cascade[1]) if not r.get("error")]
        print_cascade(label_of(None, cheap_rows), label_of(None, dear_rows),
                      cheap_rows, dear_rows)
        dump.append({"cascade": [pathlib.Path(p).name for p in args.cascade],
                     "table": cascade(cheap_rows, dear_rows)})

    if args.json:
        out = pathlib.Path(args.json)
        out.write_text(json.dumps(dump, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
