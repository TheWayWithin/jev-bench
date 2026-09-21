#!/usr/bin/env python3
"""Exact McNemar on the hard 18: is the arm-to-arm move bigger than luck?

Discordant pairs only. Two-sided exact binomial at p=0.5, computed from the
factorials rather than imported, so the number is re-derivable by hand.
"""
import json
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


def load(p, tier="A"):
    rows = {}
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if r.get("tier") == tier:
                    rows[r["id"]] = r
    return rows


def exact_two_sided(b, c):
    """b = right in A wrong in B, c = wrong in A right in B."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def compare(name_a, a, name_b, b_rows):
    ids = sorted(set(a) & set(b_rows))
    b = sum(1 for i in ids
            if a[i]["predicted"] == a[i]["label"] and b_rows[i]["predicted"] != b_rows[i]["label"])
    c = sum(1 for i in ids
            if a[i]["predicted"] != a[i]["label"] and b_rows[i]["predicted"] == b_rows[i]["label"])
    p = exact_two_sided(b, c)
    print(f"  {name_a} vs {name_b}: n={len(ids)}, "
          f"{name_a}-only-right {b}, {name_b}-only-right {c}, exact p = {p:.3f}")
    return b, c, p


print("Hard 18, schema-only arm vs reasoning-allowed arm, same model")
for name, sp, rp in PAIRS:
    compare(f"{name} schema", load(sp), f"{name} reasoning", load(rp))

print("\nHard 18, Jev (20 Sep, not re-run) vs each reasoning-allowed model")
jev = load(JEV)
for name, _sp, rp in PAIRS:
    compare("Jev", jev, f"{name} reasoning", load(rp))
