#!/usr/bin/env python3
"""Run the source-check benchmark against Jev, an LLM baseline, or both.

    python3 run.py --system jev
    python3 run.py --system llm
    python3 run.py --system both --tier A

Writes one JSONL per system to results/, one object per claim, carrying the verdict,
the confidence, wall-clock seconds and token counts. Scoring is a separate step so a
run is never lost to a scoring bug.
"""

import argparse
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
DATASET = HERE / "dataset" / "claims.jsonl"
RESULTS = HERE / "results"

LABELS = {
    "supported": "The source passage states the claim, or directly implies that it is true.",
    "unsupported": (
        "The source passage addresses what the claim asserts but does not support it as "
        "written. This covers flat contradiction, and also the case where the claim is "
        "roughly right in substance but wrong in version, figure, attribution, scope or "
        "wording, so that the sentence as written is not what the source says."
    ),
    "not_addressed": (
        "The source passage does not speak to what the claim asserts, either way. It is "
        "about something else, or it is silent on the point."
    ),
}

INSTRUCTIONS = (
    "A sentence from a published article makes a claim and cites a source. Read the "
    "source passage in `section` and decide how it relates to the claim in `claim`. "
    "Judge only against the passage given: do not use anything you may recall about "
    "the paper, and do not credit the claim for being plausible."
)


def load(tier=None):
    rows = []
    with open(DATASET, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            row = json.loads(line)
            if tier and row.get("tier") != tier:
                continue
            rows.append(row)
    return rows


def load_env():
    env_path = HERE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


# ---------------------------------------------------------------- Jev

def run_jev(rows, model):
    from typesafe_sdk import TypeSafeClient, Choice

    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set. Put it in tools/jev-bench/.env")

    questions = {"relation": Choice(instructions=INSTRUCTIONS, criteria=dict(LABELS))}
    out = []
    with TypeSafeClient() as client:
        for row in rows:
            started = time.perf_counter()
            try:
                resp = client.system_one(
                    state={"claim": row["claim"], "section": row["section"]},
                    questions=questions,
                    model=model,
                )
            except Exception as exc:  # a failed call is data, not a crash
                out.append({**meta(row), "system": "jev", "error": repr(exc)})
                continue
            secs = time.perf_counter() - started
            ans = resp.answers["relation"]
            usage = getattr(resp, "usage", None)
            out.append({
                **meta(row),
                "system": "jev",
                "model": model,
                "predicted": ans.choice,
                "confidence": float(ans.confidence),
                "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
                "seconds": round(secs, 3),
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            })
            print(f"  jev  {row['id']:<14} {ans.choice:<14} p={ans.confidence:.2f}  {secs:.2f}s")
    return out


# ---------------------------------------------------------------- LLM baseline

BASELINE_PROMPT = """You are checking a citation.

CLAIM (a sentence from a published article):
{claim}

SOURCE PASSAGE (the text it cites):
{section}

Decide how the source passage relates to the claim. The three possible answers are:

supported: {supported}
unsupported: {unsupported}
not_addressed: {not_addressed}

Judge only against the passage given. Do not use anything you may recall about the paper, and do
not credit the claim for being plausible.

Reply with JSON only, no other text, in exactly this form:
{{"verdict": "<one of supported, unsupported, not_addressed>", "confidence": <a number from 0 to 1, your probability that your verdict is correct>}}"""


VERDICT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "citation_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": list(LABELS)},
                "confidence": {"type": "number",
                               "description": "your probability that the verdict is correct, 0 to 1"},
            },
            "required": ["verdict", "confidence"],
            "additionalProperties": False,
        },
    },
}


def run_llm(rows, model):
    """Baseline through OpenRouter, which is the route Jamie already pays for.

    One key reaches every provider, so the baseline can be re-run against a different
    model without another account. The cost of that: OpenRouter adds a routing hop, so
    the latency measured here is end to end through OpenRouter and is not the provider's
    own latency. Any published latency comparison has to say so.
    """
    from openai import OpenAI

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set. Put it in tools/jev-bench/.env")

    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    out = []
    for row in rows:
        prompt = BASELINE_PROMPT.format(
            claim=row["claim"], section=row["section"], **LABELS
        )
        started = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                # Generous, because at 200 the model spent the budget reasoning in prose
                # and never reached the JSON: 14 of 18 replies came back unusable on the
                # first run. That was a harness fault, not a finding about the model.
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                response_format=VERDICT_SCHEMA,
                extra_body={"usage": {"include": True}},  # returns the real charge
            )
        except Exception as exc:
            out.append({**meta(row), "system": "llm", "error": repr(exc)})
            continue
        secs = time.perf_counter() - started
        text = (resp.choices[0].message.content or "").strip()
        verdict, conf = parse_json_verdict(text)
        usage = resp.usage
        out.append({
            **meta(row),
            "system": "llm",
            "model": model,
            "predicted": verdict,
            "confidence": conf,
            "raw": text,
            "seconds": round(secs, 3),
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            # OpenRouter reports what it actually charged, in USD. Better than a price table.
            "charged_usd": getattr(usage, "cost", None),
        })
        shown = "None" if conf is None else f"{conf:.2f}"
        print(f"  llm  {row['id']:<14} {str(verdict):<14} p={shown}  {secs:.2f}s")
    return out


def parse_json_verdict(text):
    """Pull the verdict out even when the model wraps it in a fence or a sentence."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None, None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None, None
    verdict = obj.get("verdict")
    if verdict not in LABELS:
        verdict = None
    conf = obj.get("confidence")
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = None
    return verdict, conf


def meta(row):
    return {k: row[k] for k in ("id", "tier", "source", "label") if k in row}


def write(rows, system, tag):
    RESULTS.mkdir(exist_ok=True)
    # Name the file after the model, not just the system: four baselines in one
    # afternoon and "llm-<timestamp>" tells you nothing about which one.
    model = (rows[0].get("model") or "").replace("/", "-").replace(":", "-")
    path = RESULTS / f"{system}-{model}-{tag}.jsonl" if model else RESULTS / f"{system}-{tag}.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(HERE)}  ({len(rows)} rows)")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=["jev", "llm", "both"], default="both")
    ap.add_argument("--tier", choices=["A", "B"], default=None, help="default: both tiers")
    ap.add_argument("--jev-model", default=os.environ.get("TYPESAFE_MODEL", "jev-latest"))
    ap.add_argument("--llm-model", default="anthropic/claude-sonnet-4.5",
                    help="OpenRouter model slug, e.g. openai/gpt-5.2 or google/gemini-2.5-pro")
    args = ap.parse_args()

    load_env()
    rows = load(args.tier)
    if not rows:
        sys.exit(f"no rows in {DATASET} (tier={args.tier})")
    print(f"{len(rows)} claims" + (f", tier {args.tier}" if args.tier else ", both tiers"))

    tag = time.strftime("%Y%m%d-%H%M%S")
    if args.system in ("jev", "both"):
        write(run_jev(rows, args.jev_model), "jev", tag)
    if args.system in ("llm", "both"):
        write(run_llm(rows, args.llm_model), "llm", tag)
    print(f"\nnow: python3 score.py results/jev-{tag}.jsonl results/llm-{tag}.jsonl")


if __name__ == "__main__":
    main()
