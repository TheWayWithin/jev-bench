#!/usr/bin/env python3
"""Exact McNemar: is an arm-to-arm move bigger than luck?

Discordant pairs only. Two-sided exact binomial at p=0.5, computed from the
factorials rather than imported, so the number is re-derivable by hand.

Two ways to run it.

Generic, on your own two JSONL runs over the same items:

    python3 mcnemar.py <before.jsonl> <after.jsonl> [--tier A] [--id-field id]
                        [--label-field label] [--predicted-field predicted]

Each file is one JSON object per line, with a row identifier, a true label and
a predicted label (field names configurable; defaults match this repo's own
files). Rows are matched on the identifier field, restricted to --tier if the
rows carry a tier field and --tier is given (omit --tier to use every row).

No arguments: reruns this repo's own six JevBench Test 2 comparisons, the
demo the rest of this file's numbers came from.
"""
import argparse
import json
import sys
from math import comb

PAIRS = [
    ("GPT-5.4",
     "results/llm-openai-gpt-5.4-20260920-142048.jsonl",
     "results/llm-openai-gpt-5.4-20260921-163434.jsonl"),
    ("Sonnet 5",
     "results/llm-anthropic-claude-sonnet-5-20260920-141849.jsonl",
     "results/llm-anthropic-claude-sonnet-5-20260921-163437.jsonl"),
    ("Gemini 3.1 Pro",
     "results/llm-google-gemini-3.1-pro-preview-20260920-142133.jsonl",
     "results/llm-google-gemini-3.1-pro-preview-20260921-163440.jsonl"),
]
JEV = "results/jev-20260920-114958.jsonl"


def load(p, tier="A", id_field="id", tier_field="tier"):
    rows = {}
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if tier is None or r.get(tier_field) == tier:
                    rows[r[id_field]] = r
    return rows


def exact_two_sided(b, c):
    """b = right in A wrong in B, c = wrong in A right in B."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def compare(name_a, a, name_b, b_rows, label_field="label", predicted_field="predicted"):
    ids = sorted(set(a) & set(b_rows))
    b = sum(1 for i in ids
            if a[i][predicted_field] == a[i][label_field]
            and b_rows[i][predicted_field] != b_rows[i][label_field])
    c = sum(1 for i in ids
            if a[i][predicted_field] != a[i][label_field]
            and b_rows[i][predicted_field] == b_rows[i][label_field])
    p = exact_two_sided(b, c)
    print(f"  {name_a} vs {name_b}: n={len(ids)}, "
          f"{name_a}-only-right {b}, {name_b}-only-right {c}, exact p = {p:.3f}")
    return b, c, p


def run_demo():
    print("Hard 18, schema-only arm vs reasoning-allowed arm, same model")
    for name, sp, rp in PAIRS:
        compare(f"{name} schema", load(sp), f"{name} reasoning", load(rp))

    print("\nHard 18, Jev (20 Sep, not re-run) vs each reasoning-allowed model")
    jev = load(JEV)
    for name, _sp, rp in PAIRS:
        compare("Jev", jev, f"{name} reasoning", load(rp))


def run_generic(args):
    tier = args.tier
    a = load(args.before, tier=tier, id_field=args.id_field, tier_field=args.tier_field)
    b = load(args.after, tier=tier, id_field=args.id_field, tier_field=args.tier_field)
    if not a or not b:
        sys.exit(f"no rows loaded (tier={tier!r}): check --tier, --id-field, --tier-field "
                  f"against your files' actual keys")
    compare(args.before, a, args.after, b,
            label_field=args.label_field, predicted_field=args.predicted_field)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", nargs="?", help="JSONL run before the change")
    ap.add_argument("after", nargs="?", help="JSONL run after the change")
    ap.add_argument("--tier", default=None,
                     help="restrict to rows where --tier-field equals this value "
                          "(default: use every row)")
    ap.add_argument("--id-field", default="id")
    ap.add_argument("--tier-field", default="tier")
    ap.add_argument("--label-field", default="label")
    ap.add_argument("--predicted-field", default="predicted")
    args = ap.parse_args()

    if args.before and args.after:
        run_generic(args)
    elif args.before or args.after:
        ap.error("give both <before.jsonl> and <after.jsonl>, or neither to run the repo demo")
    else:
        run_demo()


if __name__ == "__main__":
    main()
