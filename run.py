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

def run_jev(rows, model, labels=None, arm="schema"):
    """One Choice per claim. `labels` defaults to the baseline's three; the split arm passes
    SPLIT_LABELS and the answer is mapped back to the three-way label for scoring."""
    from typesafe_sdk import TypeSafeClient, Choice

    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set. Put it in tools/jev-bench/.env")

    labels = labels or LABELS
    questions = {"relation": Choice(instructions=INSTRUCTIONS, criteria=dict(labels))}
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
                out.append({**meta(row), "system": "jev", "arm": arm, "error": repr(exc)})
                continue
            secs = time.perf_counter() - started
            ans = resp.answers["relation"]
            usage = getattr(resp, "usage", None)
            rec = {
                **meta(row),
                "system": "jev",
                "model": model,
                # the versioned ID that actually answered, which an alias hides
                "served_model": getattr(resp, "model", None),
                "arm": arm,
                "predicted": SPLIT_TO_THREE.get(ans.choice, ans.choice),
                "confidence": float(ans.confidence),
                "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
                "seconds": round(secs, 3),
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            }
            if labels is not LABELS:
                rec["predicted_raw"] = ans.choice
            out.append(rec)
            print(f"  jev  {row['id']:<14} {ans.choice:<14} p={ans.confidence:.2f}  {secs:.2f}s")
    return out


# ------------------------------------------------- Test 3 (b): the compound label, split

# `unsupported` merges two different events. The split arm offers them as two options and
# maps both back to `unsupported` for scoring, so the dataset labels are untouched and the
# score is comparable with every earlier run. The two definitions are written from the `why`
# records of the dataset's `unsupported` rows; the last sentence of `altered` is written from
# the `why` records of the `supported` rows that are fair compressions (rz-05, rz-06, sb-04).
SPLIT_LABELS = {
    "supported": LABELS["supported"],
    "contradicted": (
        "The source passage addresses what the claim asserts and says something incompatible "
        "with it: the opposite, a different figure, the reverse direction of an effect, or "
        "that the thing the claim says was done or found was not."
    ),
    "altered": (
        "The claim is recognisably drawn from the source passage and roughly right in "
        "substance, but changed so that the sentence as written is not what the source says: "
        "a true figure attached to the wrong quantity, model, version or author; a hedge "
        "hardened into a certainty; a quotation assembled from separate places; or a scope "
        "wider than the passage covers. A shortening or paraphrase that leaves out detail but "
        "states nothing the passage does not is not altered: that is supported."
    ),
    "not_addressed": LABELS["not_addressed"],
}

SPLIT_TO_THREE = {"contradicted": "unsupported", "altered": "unsupported"}


# ------------------------------------------------- Test 3 (c): multi-question fan-out

# Three narrow Nouls over the same state in one call, the shape TypeSafe recommends and bills
# once on input. The rule that turns them into one of the three labels is combine_fanout(),
# fixed in the pre-registration before any fan-out run and not to be changed after.
FANOUT_QUESTIONS = {
    "addresses": (
        "A sentence from a published article makes a claim and cites a source. Does the source "
        "passage in `section` speak to what the claim in `claim` asserts, either way? Answer "
        "yes if the passage contains information that bears on whether the claim is true, even "
        "if it contradicts the claim. Judge only against the passage given."
    ),
    "contradicts": (
        "A sentence from a published article makes a claim and cites a source. Does the source "
        "passage in `section` say something incompatible with the claim in `claim`: the "
        "opposite, a different figure, the reverse direction of an effect, or that the thing "
        "the claim says was done or found was not? Judge only against the passage given."
    ),
    "faithful": (
        "A sentence from a published article makes a claim and cites a source. Is everything "
        "the claim in `claim` states either stated in the source passage in `section` or "
        "directly implied by it, with the same figures, attribution, version, scope and "
        "strength of wording? Leaving out detail is fine; adding or changing something is not. "
        "Judge only against the passage given, and do not credit the claim for being plausible."
    ),
}

FANOUT_THRESHOLD = 0.5


def combine_fanout(addresses, contradicts, faithful, t=FANOUT_THRESHOLD):
    """The pre-registered rule. Returns (label, joint probability of that label).

    not_addressed  if the passage does not speak to the claim
    supported      if it does, the claim is faithful to it, and nothing contradicts it
    unsupported    otherwise

    The joint probability treats the three answers as independent. It is reported, never used
    to pick the label.
    """
    if addresses < t:
        return "not_addressed", 1 - addresses
    if faithful >= t and contradicts < t:
        return "supported", addresses * faithful * (1 - contradicts)
    return "unsupported", addresses * (1 - faithful * (1 - contradicts))


def run_jev_fanout(rows, model):
    from typesafe_sdk import TypeSafeClient, Noul

    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY is not set. Put it in .env")

    questions = {k: Noul(instructions=v) for k, v in FANOUT_QUESTIONS.items()}
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
            except Exception as exc:
                out.append({**meta(row), "system": "jev", "arm": "fanout", "error": repr(exc)})
                continue
            secs = time.perf_counter() - started
            nouls = {k: float(resp.answers[k].noul) for k in FANOUT_QUESTIONS}
            label, joint = combine_fanout(**nouls)
            usage = getattr(resp, "usage", None)
            out.append({
                **meta(row),
                "system": "jev",
                "model": model,
                "served_model": getattr(resp, "model", None),
                "arm": "fanout",
                "predicted": label,
                "confidence": round(joint, 4),
                "nouls": nouls,
                "seconds": round(secs, 3),
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            })
            shown = " ".join(f"{k[:4]}={v:.2f}" for k, v in nouls.items())
            print(f"  jev+f {row['id']:<14} {label:<14} {shown}  {secs:.2f}s")
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


# ------------------------------------------------- LLM baseline, allowed to reason first

# Test 2 of the series. The 20 September baseline sent the frontier models straight into a
# JSON schema with nowhere to think, which is not how anyone sensible uses them, so the
# hard-set result was a result about schema-constrained models rather than about the models.
# This arm gives them a free-text scratchpad first and then asks for the same structured
# verdict, with the scratchpad in the conversation. Two calls, so the reasoning step's cost
# and latency stay separately measurable rather than being folded into one number.
#
# The scratchpad prompt carries exactly the information BASELINE_PROMPT carries — the claim,
# the passage, the same three label definitions, the same instruction to judge only against
# the passage — so the only difference between the two arms is the room to think. It says
# nothing about which label is likely, nothing about the kinds of error this dataset is built
# from, and nothing about any other system's answers.
REASONING_PROMPT = """You are checking a citation.

CLAIM (a sentence from a published article):
{claim}

SOURCE PASSAGE (the text it cites):
{section}

The question you will be asked is how the source passage relates to the claim. The three
possible answers are:

supported: {supported}
unsupported: {unsupported}
not_addressed: {not_addressed}

Before answering, think it through in plain prose. Work out what the claim asserts, what the
passage actually states, and where the two do and do not line up. Quote the words from the
passage that decide it.

Judge only against the passage given. Do not use anything you may recall about the paper, and do
not credit the claim for being plausible.

Do not give your answer yet. This step is the reasoning only. Keep it under 200 words."""


VERDICT_FOLLOWUP = """Now give your answer, choosing one of the three defined above.

Reply with JSON only, no other text, in exactly this form:
{{"verdict": "<one of supported, unsupported, not_addressed>", "confidence": <a number from 0 to 1, your probability that your verdict is correct>}}"""


def _charge(usage):
    """OpenRouter's own reported charge for one call, in USD, or None if it withheld it."""
    return getattr(usage, "cost", None)


def run_llm_reasoning(rows, model):
    """Same baseline, same schema, but with a free-text reasoning turn in front of it.

    `seconds`, `input_tokens`, `output_tokens` and `charged_usd` are the totals across both
    calls, because that is what the arm costs a user and it keeps score.py and
    risk_coverage.py working against these files unmodified. The per-step figures are kept
    alongside under `reasoning_*` and `verdict_*` so the split is re-derivable from the raw
    JSONL by somebody who was not here.
    """
    from openai import OpenAI

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set. Put it in .env")

    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    out = []
    for row in rows:
        think = REASONING_PROMPT.format(
            claim=row["claim"], section=row["section"], **LABELS
        )
        messages = [{"role": "user", "content": think}]

        started = time.perf_counter()
        try:
            r1 = client.chat.completions.create(
                model=model,
                max_tokens=1500,
                messages=messages,
                extra_body={"usage": {"include": True}},
            )
        except Exception as exc:
            out.append({**meta(row), "system": "llm", "arm": "reasoning",
                        "model": model, "error": f"reasoning step: {exc!r}"})
            continue
        secs_r = time.perf_counter() - started
        reasoning = (r1.choices[0].message.content or "").strip()

        messages.append({"role": "assistant", "content": reasoning})
        messages.append({"role": "user", "content": VERDICT_FOLLOWUP.format()})

        started = time.perf_counter()
        try:
            r2 = client.chat.completions.create(
                model=model,
                max_tokens=1500,
                messages=messages,
                response_format=VERDICT_SCHEMA,
                extra_body={"usage": {"include": True}},
            )
        except Exception as exc:
            out.append({**meta(row), "system": "llm", "arm": "reasoning",
                        "model": model, "reasoning": reasoning,
                        "error": f"verdict step: {exc!r}"})
            continue
        secs_v = time.perf_counter() - started

        text = (r2.choices[0].message.content or "").strip()
        verdict, conf = parse_json_verdict(text)
        u1, u2 = r1.usage, r2.usage
        c1, c2 = _charge(u1), _charge(u2)
        r_in = getattr(u1, "prompt_tokens", 0) or 0
        r_out = getattr(u1, "completion_tokens", 0) or 0
        v_in = getattr(u2, "prompt_tokens", 0) or 0
        v_out = getattr(u2, "completion_tokens", 0) or 0

        out.append({
            **meta(row),
            "system": "llm",
            "model": model,
            "arm": "reasoning",
            "predicted": verdict,
            "confidence": conf,
            "reasoning": reasoning,
            "raw": text,
            # totals across both calls: what the arm actually costs and takes
            "seconds": round(secs_r + secs_v, 3),
            "input_tokens": r_in + v_in,
            "output_tokens": r_out + v_out,
            "charged_usd": None if (c1 is None or c2 is None) else c1 + c2,
            # the split, so the reasoning step is attributable on its own
            "reasoning_seconds": round(secs_r, 3),
            "reasoning_input_tokens": r_in,
            "reasoning_output_tokens": r_out,
            "reasoning_charged_usd": c1,
            "verdict_seconds": round(secs_v, 3),
            "verdict_input_tokens": v_in,
            "verdict_output_tokens": v_out,
            "verdict_charged_usd": c2,
        })
        shown = "None" if conf is None else f"{conf:.2f}"
        print(f"  llm+r {row['id']:<14} {str(verdict):<14} p={shown}  "
              f"{secs_r:.2f}s+{secs_v:.2f}s  {r_out}w")
    return out


# ------------------------------------------------- Test 3 (b), the same split for the LLMs

# BASELINE_PROMPT with the four split definitions in place of the three. Nothing else changes:
# same framing, same instruction to judge only against the passage, same JSON shape.
SPLIT_PROMPT = """You are checking a citation.

CLAIM (a sentence from a published article):
{claim}

SOURCE PASSAGE (the text it cites):
{section}

Decide how the source passage relates to the claim. The four possible answers are:

supported: {supported}
contradicted: {contradicted}
altered: {altered}
not_addressed: {not_addressed}

Judge only against the passage given. Do not use anything you may recall about the paper, and do
not credit the claim for being plausible.

Reply with JSON only, no other text, in exactly this form:
{{"verdict": "<one of supported, contradicted, altered, not_addressed>", "confidence": <a number from 0 to 1, your probability that your verdict is correct>}}"""

SPLIT_SCHEMA = json.loads(json.dumps(VERDICT_SCHEMA))
SPLIT_SCHEMA["json_schema"]["name"] = "citation_verdict_split"
SPLIT_SCHEMA["json_schema"]["schema"]["properties"]["verdict"]["enum"] = list(SPLIT_LABELS)


def run_llm_split(rows, model):
    """run_llm() with the split labels. `predicted_raw` keeps the four-way answer; `predicted`
    is mapped back to the three-way label so score.py and mcnemar.py read it unchanged."""
    from openai import OpenAI

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set. Put it in .env")

    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    out = []
    for row in rows:
        prompt = SPLIT_PROMPT.format(claim=row["claim"], section=row["section"], **SPLIT_LABELS)
        started = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                response_format=SPLIT_SCHEMA,
                extra_body={"usage": {"include": True}},
            )
        except Exception as exc:
            out.append({**meta(row), "system": "llm", "arm": "split", "model": model,
                        "error": repr(exc)})
            continue
        secs = time.perf_counter() - started
        text = (resp.choices[0].message.content or "").strip()
        raw, conf = parse_json_verdict(text, allowed=SPLIT_LABELS)
        usage = resp.usage
        out.append({
            **meta(row),
            "system": "llm",
            "model": model,
            "arm": "split",
            "predicted": SPLIT_TO_THREE.get(raw, raw),
            "predicted_raw": raw,
            "confidence": conf,
            "raw": text,
            "seconds": round(secs, 3),
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "charged_usd": getattr(usage, "cost", None),
        })
        shown = "None" if conf is None else f"{conf:.2f}"
        print(f"  llm+s {row['id']:<14} {str(raw):<14} p={shown}  {secs:.2f}s")
    return out


def parse_json_verdict(text, allowed=None):
    """Pull the verdict out even when the model wraps it in a fence or a sentence."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None, None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None, None
    verdict = obj.get("verdict")
    if verdict not in (allowed or LABELS):
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
    ap.add_argument("--arm", choices=["schema", "reasoning", "split", "fanout"], default="schema",
                    help="schema: straight into the JSON verdict, the 20 September baseline. "
                         "reasoning: a free-text scratchpad first, then the same verdict. "
                         "split: `unsupported` offered as contradicted and altered, scored as "
                         "unsupported (Test 3b). fanout: three Nouls in one call, combined by a "
                         "fixed rule, Jev only (Test 3c).")
    ap.add_argument("--label", default=None,
                    help="prefix for the timestamp in the output filename, e.g. t4-r1, so "
                         "repeat runs can be told apart by name")
    args = ap.parse_args()

    load_env()
    rows = load(args.tier)
    if not rows:
        sys.exit(f"no rows in {DATASET} (tier={args.tier})")
    print(f"{len(rows)} claims" + (f", tier {args.tier}" if args.tier else ", both tiers"))

    tag = time.strftime("%Y%m%d-%H%M%S")
    if args.label:
        tag = f"{args.label}-{tag}"
    if args.system in ("jev", "both"):
        if args.arm == "fanout":
            out = run_jev_fanout(rows, args.jev_model)
        elif args.arm == "split":
            out = run_jev(rows, args.jev_model, labels=SPLIT_LABELS, arm="split")
        else:
            out = run_jev(rows, args.jev_model)
        write(out, "jev", tag)
    if args.system in ("llm", "both"):
        runner = {"reasoning": run_llm_reasoning, "split": run_llm_split}.get(args.arm, run_llm)
        if args.arm == "fanout":
            sys.exit("the fan-out arm is Jev only")
        write(runner(rows, args.llm_model), "llm", tag)
    print(f"\nnow: python3 score.py results/jev-{tag}.jsonl results/llm-{tag}.jsonl")


if __name__ == "__main__":
    main()
