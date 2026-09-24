#!/usr/bin/env python3
"""Test 1 (T-809): Jev against Claude Sonnet on Jamie's triage. Pre-registration:
test1-preregistration.md. Nothing here may change after the first scored run except to
fix a crash, and any such fix is recorded in the verdict file.

    python3 test1.py smoke                          # one Jev call on a made-up note
    python3 test1.py run --task routing --system jev --label r1
    python3 test1.py run --task ideas   --system llm --label r3

Reuses the jev-bench calling pattern (typesafe_sdk Choice, OpenRouter for the LLM with
OpenRouter's own charge recorded) and reads the same .env, so no new key is needed.
Writes one JSONL per run to results/. Scoring is analyse.py, a separate step, so a run is
never lost to a scoring bug.
"""

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent / "jev-bench"
DATA = HERE / "data"
RESULTS = HERE / "results"

JEV_MODEL = "jev-1.13.0"                 # pinned, as in the jev-bench five-run test
LLM_MODEL = "anthropic/claude-sonnet-5"  # the current Sonnet, via OpenRouter
JEV_PRICE_PER_MTOK = 0.042               # tools/jev-bench/prices.json, read 2026-09-20
WORKERS = 6

# ------------------------------------------------------------------ the two tasks

# The homes, worded from BRAIN-SCHEMA.md ("Homes" and "The Filing Decision"). `delete` is
# offered because the schema offers it; no item in the key carries it.
ROUTING_OPTIONS = {
    "mission-control": (
        "About a specific project, product, sprint task, operational decision or the "
        "direction of Jamie's work: project specs, briefs, product status files."),
    "income-bridge": (
        "Outward-facing work products for income opportunities: board papers, proposals, "
        "scoping docs, applications and the like, written for a third party rather than for "
        "Jamie, where a third party is meant to read it and it exists to win or deliver paid "
        "work."),
    "books": (
        "A book manuscript or chapter, or material belonging to a book Jamie is writing "
        "(for example The Way Within). Not notes about books he has read."),
    "efformism": "Anything relating to the Efformism framework: treatise, papers, notes, drafts.",
    "content": (
        "Anything being created for publication: an idea for a post, a draft being written, "
        "or a shipped piece and its social variants."),
    "knowledge": (
        "Learning material Jamie has read or watched and wants to retain: highlights, "
        "article notes, video, book and course notes, research cards and deep dives, "
        "research insights, transcripts, topic pages."),
    "reference": (
        "Reusable reference material to look up again, copy or follow: templates, "
        "instruction blocks, how-to docs, SOPs, runbooks, product and market research data. "
        "Not project-specific, not learning material."),
    "delete": "Junk, stale, or duplicated elsewhere.",
}

ROUTING_INSTRUCTIONS = (
    "This note is in the inbox of Jamie Watters's second-brain vault. Decide which home it "
    "should be filed to under the vault's filing rules. `title` is the note's title and "
    "`note` is the start of its text.")

# Jamie's priorities, read 2026-09-23 [source redacted for publication]. Both
# systems get the same context, fixed before any run.
# [Redacted for publication, 24 Sep 2026: the personal profile used only by the ideas task.
# The ideas task was never run (Test 1 verdict, deviation 2), so no result depends on it.]
IDEAS_CONTEXT = "[withheld]"

IDEAS_OPTIONS = {
    "yes": "Worth doing: raise it as a real task now.",
    "no": "Not worth doing: decline it for good.",
    "not_now": "Possibly worth doing, but not now: bring it back another day.",
}

IDEAS_INSTRUCTIONS = (
    "A proposed action from Jamie's ideas queue, drawn from a video, book or research note "
    "he filed. `about_jamie` describes him and his priorities. `proposal` is the action, "
    "`tag` its kind and `source` the note it came from. Decide what Jamie should do with it.")


def routing_state(row):
    return {"title": row["title"], "note": row["text"]}


def ideas_state(row):
    return {"about_jamie": IDEAS_CONTEXT, "proposal": row["proposal"], "tag": row["tag"],
            "source": row["source"]}


TASKS = {
    "routing": (DATA / "routing-key.jsonl", ROUTING_OPTIONS, ROUTING_INSTRUCTIONS, routing_state),
    "ideas": (DATA / "ideas-key.jsonl", IDEAS_OPTIONS, IDEAS_INSTRUCTIONS, ideas_state),
}

LLM_PROMPT = """{instructions}

The item, as fields:
{state}

The possible answers are:
{options}

Reply with JSON only, no other text, in exactly this form:
{{"answer": "<one of {names}>", "confidence": <a number from 0 to 1, your probability that your answer is the one Jamie would give>}}"""


# ------------------------------------------------------------------ plumbing

def load_env():
    for line in (BENCH / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def meta(row):
    return {"id": row["id"], "label": row.get("label")}


# ------------------------------------------------------------------ Jev

def jev_one(client, row, options, instructions, state_fn):
    from typesafe_sdk import Choice
    q = {"decision": Choice(instructions=instructions, criteria=dict(options))}
    started = time.perf_counter()
    try:
        resp = client.system_one(state=state_fn(row), questions=q, model=JEV_MODEL)
    except Exception as exc:  # a failed call is data, not a crash
        return {**meta(row), "system": "jev", "model": JEV_MODEL, "error": repr(exc)}
    ans = resp.answers["decision"]
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "input_tokens", 0) or 0
    return {
        **meta(row),
        "system": "jev",
        "model": JEV_MODEL,
        "served_model": getattr(resp, "model", None),
        "predicted": ans.choice,
        "confidence": float(ans.confidence),
        "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
        "seconds": round(time.perf_counter() - started, 3),
        "input_tokens": tin,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cost_usd": tin / 1e6 * JEV_PRICE_PER_MTOK,
        "cost_basis": "price table: input tokens x $0.042/MTok, output free",
    }


def run_jev(rows, options, instructions, state_fn):
    from typesafe_sdk import TypeSafeClient
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set in tools/jev-bench/.env")
    with TypeSafeClient() as client:
        with cf.ThreadPoolExecutor(WORKERS) as ex:
            return list(ex.map(lambda r: jev_one(client, r, options, instructions, state_fn),
                               rows))


# ------------------------------------------------------------------ Claude Sonnet

def llm_schema(options):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "triage_answer",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "enum": list(options)},
                    "confidence": {"type": "number"},
                },
                "required": ["answer", "confidence"],
                "additionalProperties": False,
            },
        },
    }


def parse(text, options):
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None, None
    try:
        obj = json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None, None
    ans = obj.get("answer") if obj.get("answer") in options else None
    try:
        conf = float(obj.get("confidence"))
    except (TypeError, ValueError):
        conf = None
    return ans, conf


def llm_one(client, row, options, instructions, state_fn):
    prompt = LLM_PROMPT.format(
        instructions=instructions,
        state=json.dumps(state_fn(row), ensure_ascii=False, indent=2),
        options="\n".join(f"{k}: {v}" for k, v in options.items()),
        names=", ".join(options),
    )
    started = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=1500,  # jev-bench found 200 too few; temperature left at the default
            messages=[{"role": "user", "content": prompt}],
            response_format=llm_schema(options),
            extra_body={"usage": {"include": True}},
        )
    except Exception as exc:
        return {**meta(row), "system": "llm", "model": LLM_MODEL, "error": repr(exc)}
    text = (resp.choices[0].message.content or "").strip()
    ans, conf = parse(text, options)
    u = resp.usage
    return {
        **meta(row),
        "system": "llm",
        "model": LLM_MODEL,
        "served_model": getattr(resp, "model", None),
        "predicted": ans,
        "confidence": conf,
        "raw": text,
        "seconds": round(time.perf_counter() - started, 3),
        "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
        "output_tokens": getattr(u, "completion_tokens", 0) or 0,
        "cost_usd": getattr(u, "cost", None),
        "cost_basis": "OpenRouter's reported charge",
    }


def run_llm(rows, options, instructions, state_fn):
    from openai import OpenAI
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set in tools/jev-bench/.env")
    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(lambda r: llm_one(client, r, options, instructions, state_fn), rows))


# ------------------------------------------------------------------ commands

def smoke():
    """Can one Choice hold all eight homes? One call on a note that is not in the key."""
    from typesafe_sdk import TypeSafeClient
    fake = {"id": "smoke", "title": "Checklist for renewing a domain",
            "text": "Steps to follow each year when a domain renewal notice arrives: check "
                    "auto-renew, confirm the card on file, note the new expiry date."}
    with TypeSafeClient() as client:
        rec = jev_one(client, fake, ROUTING_OPTIONS, ROUTING_INSTRUCTIONS, routing_state)
    print(json.dumps(rec, indent=2))


def run(task, system, label):
    path, options, instructions, state_fn = TASKS[task]
    rows = load_rows(path)
    if task == "ideas" and any(r.get("label") not in IDEAS_OPTIONS for r in rows):
        sys.exit("ideas-key.jsonl has rows without Jamie's label")
    fn = run_jev if system == "jev" else run_llm
    t0 = time.time()
    out = fn(rows, options, instructions, state_fn)
    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"{task}-{system}-{label}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with open(dest, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps({**r, "task": task, "run": label}, ensure_ascii=False) + "\n")
    errs = sum(1 for r in out if r.get("error") or not r.get("predicted"))
    print(f"wrote {dest.relative_to(HERE)}  {len(out)} rows, {errs} unusable, "
          f"{time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("smoke")
    r = sub.add_parser("run")
    r.add_argument("--task", choices=list(TASKS), required=True)
    r.add_argument("--system", choices=["jev", "llm"], required=True)
    r.add_argument("--label", required=True)
    args = ap.parse_args()
    load_env()
    if args.cmd == "smoke":
        smoke()
    else:
        run(args.task, args.system, args.label)


if __name__ == "__main__":
    main()
