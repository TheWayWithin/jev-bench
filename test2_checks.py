#!/usr/bin/env python3
"""
test2_checks.py — the per-row and per-model checks behind the Test 2 article
(reasoning-allowed rerun), each as one subcommand so verify-figures.py's manifest
can call them as single-line commands.

    python3 test2_checks.py <subcommand> [args...]

Run from the repo root or anywhere; paths are resolved relative to this file's directory.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def resolve(p):
    if os.path.isabs(p) or os.path.exists(p):
        return p
    cand = os.path.join(HERE, p)
    return cand if os.path.exists(cand) else p


def load_all(p):
    with open(resolve(p), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def load_tier_a(p):
    return {r["id"]: r for r in load_all(p) if r.get("tier") == "A"}


def cmd_identical(args):
    s = load_tier_a(args.schema)
    r = load_tier_a(args.reasoning)
    diffs = [cid for cid in s if s[cid]["predicted"] != r[cid]["predicted"]]
    print(f"rows with different predicted label: {len(diffs)}")


def cmd_harsher_summary(args):
    pairs = [
        ("results/llm-openai-gpt-5.4-20260920-142048.jsonl",
         "results/llm-openai-gpt-5.4-20260921-163434.jsonl"),
        ("results/llm-anthropic-claude-sonnet-5-20260920-141849.jsonl",
         "results/llm-anthropic-claude-sonnet-5-20260921-163437.jsonl"),
        ("results/llm-google-gemini-3.1-pro-preview-20260920-142133.jsonl",
         "results/llm-google-gemini-3.1-pro-preview-20260921-163440.jsonl"),
    ]
    harsher = harsher_wrong = softer = softer_right = 0
    for sp, rp in pairs:
        s, r = load_tier_a(sp), load_tier_a(rp)
        for cid in s:
            if s[cid]["predicted"] == r[cid]["predicted"]:
                continue
            after_ok = r[cid]["predicted"] == r[cid]["label"]
            if r[cid]["predicted"] == "unsupported" and s[cid]["predicted"] != "unsupported":
                harsher += 1
                if not after_ok:
                    harsher_wrong += 1
            else:
                softer += 1
                if after_ok:
                    softer_right += 1
    print(f"harsher: {harsher} harsher_wrong: {harsher_wrong} softer: {softer} softer_right: {softer_right}")


def cmd_lead_widened(args):
    jev = load_tier_a("results/jev-20260920-114958.jsonl")
    gpt_schema = load_tier_a("results/llm-openai-gpt-5.4-20260920-142048.jsonl")
    gpt_reasoning = load_tier_a("results/llm-openai-gpt-5.4-20260921-163434.jsonl")

    def acc(rows):
        return sum(1 for r in rows.values() if r["predicted"] == r["label"])

    jev_n = acc(jev)
    lead_schema = (jev_n - acc(gpt_schema)) / 18 * 100
    lead_reasoning = (jev_n - acc(gpt_reasoning)) / 18 * 100
    direction = "widened" if lead_reasoning > lead_schema else "narrowed"
    print(f"schema-only lead: {lead_schema:.1f} points  "
          f"reasoning-allowed lead: {lead_reasoning:.1f} points  {direction}")


def cmd_changed_summary(args):
    pairs = [
        ("results/llm-openai-gpt-5.4-20260920-142048.jsonl",
         "results/llm-openai-gpt-5.4-20260921-163434.jsonl"),
        ("results/llm-anthropic-claude-sonnet-5-20260920-141849.jsonl",
         "results/llm-anthropic-claude-sonnet-5-20260921-163437.jsonl"),
        ("results/llm-google-gemini-3.1-pro-preview-20260920-142133.jsonl",
         "results/llm-google-gemini-3.1-pro-preview-20260921-163440.jsonl"),
    ]
    changed = r2w = w2r = 0
    for sp, rp in pairs:
        s, r = load_tier_a(sp), load_tier_a(rp)
        for cid in s:
            sc = s[cid]["predicted"] == s[cid]["label"]
            rc = r[cid]["predicted"] == r[cid]["label"]
            if s[cid]["predicted"] != r[cid]["predicted"]:
                changed += 1
                if sc and not rc:
                    r2w += 1
                if not sc and rc:
                    w2r += 1
    print(f"changed: {changed} right_to_wrong: {r2w} wrong_to_right: {w2r}")


def cmd_claim_text(args):
    with open(resolve(args.file), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            r = json.loads(line)
            if r["id"] == args.id:
                print(r["claim"])
                return
    sys.exit(f"no claim with id {args.id!r} in {args.file}")


def cmd_row(args):
    rows = {r["id"]: r for r in load_all(args.file)}
    r = rows[args.id]
    print(r["label"], r["predicted"], r["confidence"])
    if "reasoning" not in r:
        return
    if args.full:
        print(r["reasoning"])
    else:
        print(r["reasoning"][:args.chars])


def cmd_flips(args):
    s, r = load_tier_a(args.schema), load_tier_a(args.reasoning)
    for cid in sorted(s):
        sc = s[cid]["predicted"] == s[cid]["label"]
        rc = r[cid]["predicted"] == r[cid]["label"]
        if sc and not rc:
            print(cid, s[cid]["label"], "->", r[cid]["predicted"])


def cmd_verdict_tokens(args):
    for path in args.files:
        toks = [r["verdict_output_tokens"] for r in load_all(path)]
        print(os.path.basename(path)[:20], min(toks), max(toks))


def cmd_scratchpad_range(args):
    lo = hi = None
    for path in args.files:
        for r in load_all(path):
            n = len(r["reasoning"].split())
            lo = n if lo is None or n < lo else lo
            hi = n if hi is None or n > hi else hi
    print("min", lo, "max", hi)


def cmd_ignored_instruction(args):
    label_re = re.compile(r"\b(supported|unsupported|not_addressed)\b", re.I)
    for name, path in zip(args.names, args.files):
        n = 0
        for r in load_all(path):
            tail = " ".join(r["reasoning"].split()[-15:])
            if label_re.search(tail):
                n += 1
        print(name, n, "of", len(load_all(path)))


def cmd_jev_contested(args):
    rows = {r["id"]: r for r in load_all(args.file)}
    for cid in args.ids:
        r = rows[cid]
        print(cid, r["predicted"] == r["label"], r["confidence"])


def cmd_verdict_share(args):
    rows = load_all(args.file)
    vc = sum(r["verdict_charged_usd"] for r in rows) / len(rows)
    tc = sum(r["charged_usd"] for r in rows) / len(rows)
    vs = sum(r["verdict_seconds"] for r in rows) / len(rows)
    ts = sum(r["seconds"] for r in rows) / len(rows)
    print(f"{vc / tc:.1%} {vs / ts:.1%}")


def cmd_cost_latency_multiples(args):
    def costsecs(p):
        rows = load_all(p)
        cost = sum(r["charged_usd"] for r in rows) / len(rows)
        secs = sum(r["seconds"] for r in rows) / len(rows)
        return cost, secs

    pairs = [
        ("GPT-5.4",
         "results/llm-openai-gpt-5.4-20260920-142048.jsonl",
         "results/llm-openai-gpt-5.4-20260921-163434.jsonl"),
        ("Sonnet 5",
         "results/llm-anthropic-claude-sonnet-5-20260920-141849.jsonl",
         "results/llm-anthropic-claude-sonnet-5-20260921-163437.jsonl"),
        ("Gemini",
         "results/llm-google-gemini-3.1-pro-preview-20260920-142133.jsonl",
         "results/llm-google-gemini-3.1-pro-preview-20260921-163440.jsonl"),
    ]
    for name, sp, rp in pairs:
        sc, ss = costsecs(sp)
        rc, rs = costsecs(rp)
        print(f"{name}: cost x{rc / sc:.2f} latency x{rs / ss:.2f}")


def cmd_run_gap(args):
    from datetime import datetime as dt
    pairs = [
        ("20260920-142048", "20260921-163434"),
        ("20260920-141849", "20260921-163437"),
        ("20260920-142133", "20260921-163440"),
    ]
    hours = [round((dt.strptime(b, "%Y%m%d-%H%M%S") -
                    dt.strptime(a, "%Y%m%d-%H%M%S")).total_seconds() / 3600, 1)
             for a, b in pairs]
    print(hours)


def cmd_cost_multiple(args):
    # Costs as separately verified by the score.py claims elsewhere in the manifest,
    # so this takes the two figures directly rather than re-deriving Jev's cost, which
    # score.py computes from token counts at the published rate, not a charged_usd field.
    print(f"{args.b / args.a:.0f}x")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("identical")
    p.add_argument("schema")
    p.add_argument("reasoning")
    p.set_defaults(func=cmd_identical)

    p = sub.add_parser("lead-widened")
    p.set_defaults(func=cmd_lead_widened)

    p = sub.add_parser("changed-summary")
    p.set_defaults(func=cmd_changed_summary)

    p = sub.add_parser("harsher-summary")
    p.set_defaults(func=cmd_harsher_summary)

    p = sub.add_parser("claim-text")
    p.add_argument("file")
    p.add_argument("id")
    p.set_defaults(func=cmd_claim_text)

    p = sub.add_parser("row")
    p.add_argument("file")
    p.add_argument("id")
    p.add_argument("--chars", type=int, default=400)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=cmd_row)

    p = sub.add_parser("flips")
    p.add_argument("schema")
    p.add_argument("reasoning")
    p.set_defaults(func=cmd_flips)

    p = sub.add_parser("verdict-tokens")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_verdict_tokens)

    p = sub.add_parser("scratchpad-range")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_scratchpad_range)

    p = sub.add_parser("ignored-instruction")
    p.add_argument("--names", nargs="+", required=True)
    p.add_argument("--files", nargs="+", required=True)
    p.set_defaults(func=cmd_ignored_instruction)

    p = sub.add_parser("jev-contested")
    p.add_argument("file")
    p.add_argument("ids", nargs="+")
    p.set_defaults(func=cmd_jev_contested)

    p = sub.add_parser("verdict-share")
    p.add_argument("file")
    p.set_defaults(func=cmd_verdict_share)

    p = sub.add_parser("cost-latency-multiples")
    p.set_defaults(func=cmd_cost_latency_multiples)

    p = sub.add_parser("run-gap")
    p.set_defaults(func=cmd_run_gap)

    p = sub.add_parser("cost-multiple")
    p.add_argument("a", type=float)
    p.add_argument("b", type=float)
    p.set_defaults(func=cmd_cost_multiple)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
