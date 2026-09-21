# Verdict, Test 2 — let the big models think first

**The question.** Does Jev still win the hard half when the frontier models are allowed to reason
before they answer, instead of being forced straight into a JSON verdict? This was weakness 1 in
the README and the one finding that could have overturned the first article.

**The answer: the gap did not close.** Given a free-text scratchpad before the same structured
verdict, not one of the three frontier models improved on the hard 18. Two scored lower and one
scored identically, claim for claim. Jev's lead over the best of them goes from 11.1 points to
16.7. It cost between 2.4 and 4.2 times more per claim to find that out.

**But the drops are not significant, and the honest headline is "reasoning did not help", not
"reasoning made them worse".** See Against the numbers below.

Runs made 21 September 2026, 42 claims, three models, one run each, through OpenRouter, exactly as
the 20 September baseline was run. Jev was not re-run: its row is the 20 September run unchanged.
This file carries the date of the article it feeds; the runs and the raw files are 21 September,
which is what their timestamps say.

Raw per-claim output:
`llm-openai-gpt-5.4-20260921-163434.jsonl`,
`llm-anthropic-claude-sonnet-5-20260921-163437.jsonl`,
`llm-google-gemini-3.1-pro-preview-20260921-163440.jsonl`.
Scored: `2026-09-21-test2-reasoning-scored.txt`. Thresholds: `2026-09-21-test2-risk-coverage.txt`.

## What the new arm does

Two calls per claim, in `run_llm_reasoning()`.

The first gives the model the claim, the passage, and the same three label definitions the
schema-only arm got, then asks it to think in plain prose, under 200 words, and not to answer yet.
The second asks for the verdict in the same JSON schema as before, with the scratchpad sitting in
the conversation.

Two calls rather than one relaxed call, so the reasoning step's cost and latency are separately
measurable instead of buried in a single number. Every row in the JSONL carries
`reasoning_seconds`, `verdict_seconds`, `reasoning_charged_usd`, `verdict_charged_usd` and the
token counts for each step, and the totals are the sums of those parts: checked row by row, 126 of
126 consistent.

The scratchpad prompt carries the same information as `BASELINE_PROMPT` and no more. It names no
label as likely, says nothing about how the labels are distributed, says nothing about the kinds of
error this set is built from, and mentions no other system.

## The numbers

| | all 42 | the easy 24 | the hard 18 | cost per claim | seconds |
|---|---|---|---|---|---|
| **Jev** `jev-latest`, not re-run | 85.7% | 91.7% | **77.8%** | **$0.000025** | **0.23** |
| GPT-5.4, schema only | 85.7% | 100% | 66.7% | $0.001289 | 1.01 |
| GPT-5.4, reasoning allowed | 83.3% | 100% | 61.1% | $0.005450 | 3.77 |
| Sonnet 5, schema only | 85.7% | 100% | 66.7% | $0.002228 | 2.76 |
| Sonnet 5, reasoning allowed | 76.2% | 100% | 44.4% | $0.006439 | 6.23 |
| Gemini 3.1 Pro, schema only | 81.0% | 100% | 55.6% | $0.004824 | 3.78 |
| Gemini 3.1 Pro, reasoning allowed | 78.6% | 95.8% | 55.6% | $0.011545 | 8.71 |

Cost is measured, not estimated: OpenRouter reports what it charged for each of the two calls and
both are in the JSONL. Jev's is computed from its own token counts at the published $0.042 per
million input tokens with free output.

**On the hard 18, per model:** GPT-5.4 12 of 18 correct becomes 11 of 18, −5.6 points. Sonnet 5 12
of 18 becomes 8 of 18, −22.2 points. Gemini 3.1 Pro is 10 of 18 in both arms and the same 10 rows.

**Jev still leads.** 14 of 18 against the best reasoning-allowed model, GPT-5.4's 11 of 18:
**+16.7 points, three claims.** Against the best frontier score in either arm, the 12 of 18 that
GPT-5.4 and Sonnet 5 both managed schema-only, the lead is +11.1 points, two claims.

## What the reasoning arm cost

| | cost multiple | latency multiple | of which, the thinking step |
|---|---|---|---|
| GPT-5.4 | 4.23x | 3.74x | $0.003505 and 2.63s of $0.005450 and 3.77s |
| Sonnet 5 | 2.89x | 2.26x | $0.003885 and 4.27s of $0.006439 and 6.23s |
| Gemini 3.1 Pro | 2.39x | 2.31x | $0.006413 and 4.79s of $0.011545 and 8.71s |

Scratchpads ran 42 to 196 words, mean 106 to 130 depending on the model.

Against Jev, the cheapest reasoning-allowed arm is about 220 times the cost per claim and about 16
times the latency, for three fewer correct answers out of 18.

## Against the numbers: what cannot be claimed

Exact McNemar on the discordant pairs in the hard 18. Run `python3 mcnemar.py` from the repo root:
it needs no keys and reads the JSONL files that are already here.

- GPT-5.4: 2 rows right only schema-only, 1 right only with reasoning. **p = 1.000.**
- Sonnet 5: 5 rows right only schema-only, 1 right only with reasoning. **p = 0.219.**
- Gemini 3.1 Pro: 0 and 0. Identical answers on all 18. **p = 1.000.**

**So "reasoning made the frontier models worse" is not a supportable sentence.** What the run
supports is narrower and still answers the question that was asked: reasoning did not close the
gap, for any of the three, and it did not produce a single net gain on the hard set anywhere.

The same test on Jev against each reasoning-allowed model is one-sided every time — Jev is right
and the model wrong on 3, 6 and 4 rows respectively, and the reverse never happens once in 54
comparisons — but only the Sonnet 5 comparison clears p = 0.05 (0.031, and it would not survive
correction for three comparisons). GPT-5.4 is p = 0.250, Gemini p = 0.125.

## Why the answers moved, where they moved

Nine verdicts changed on the hard set: seven from right to wrong, two from wrong to right. Five of
the nine moved toward a harsher reading and four of those five were wrong; two moved toward a
softer one; two moved between `unsupported` and `not_addressed`.

The harsher moves are where the damage is. Four of Sonnet 5's five new errors are one shape: a claim whose
true label is `supported`, talked down to `unsupported` after the model found a wording or
provenance objection in its own scratchpad. `rz-05`, `rz-06`, `sb-04`, `sb-06`.

Read the `reasoning` field on those rows and the objections are mostly *correct about the passage*.
The models notice that the passage never names the paper the claim is about, or that the claim
compresses a method, and decline to grant it. The labels require granting it. Deliberation surfaces
an ambiguity in the dataset that a straight-to-schema answer skates over.

That is the most useful thing this run produced and it is a finding against the benchmark, not
against the models. It goes to Test 3, which was already going to split the compound `unsupported`
label.

## Honest limits

1. **n = 18 on the set that carries the headline.** One claim is 5.6 points. No per-model drop is
   statistically significant.
2. **One run per model per arm.** Temperature is unset on both calls, no seed, no repeats, so there
   is no variance estimate anywhere in this. Test 4 exists for exactly this reason and should run
   before any of these numbers is leaned on hard.
3. **This arm measures "think, then transcribe", not "think, then decide".** The verdict call
   returned 21 to 23 output tokens on every GPT-5.4 row and 22 to 25 on every Sonnet 5 row: it
   emits the JSON and does not re-deliberate. Gemini's verdict call is the exception and ranges
   from 14 to 1453 tokens. So for two of the three models the scratchpad effectively *is* the
   decision.
4. **"Do not give your answer yet" was ignored on a minority of claims.** Counting only an explicit
   label in a scratchpad's closing lines: 11 of 42 for GPT-5.4, 6 of 42 for Gemini, 1 of 42 for
   Sonnet 5. Where it happens, the verdict step can only ratify it.
5. **Gemini 3.1 Pro's overall drop, 81.0% to 78.6%, is entirely one constructed control**,
   `ctl-10`. Its hard-18 answers are identical across the arms.
6. **The 200-word cap on the scratchpad is an uncontrolled variable.** The schema-only arm had no
   word cap, because it was not asked for prose at all. The cap was never breached: the longest
   scratchpad is 196 words.
7. **Several labels on the flipped rows are contestable**, and the reasoning text argues the other
   side coherently on `ctl-10`, `rz-05`, `rz-07` and `sb-04`. The labels are single-annotator with
   no reported agreement, which is weakness 7 in the README and is not fixed here.
8. **`unsupported` remains a compound label**, and `rz-07` and `sb-07` sit on a boundary the stated
   definitions arguably cannot resolve: a passage that explicitly says it is silent on a point is
   both "addressing what the claim asserts" and "not speaking to it".
9. **Four of Jev's correct answers on the contested rows are below its own 0.5 confidence**:
   `rz-05` at 0.24, `sb-07` at 0.29, `sb-06` at 0.37, `sb-05` at 0.49. Part of the lead is Jev
   being unsure and right.
10. **Latency is end to end through OpenRouter and this arm makes two round trips**, so its routing
    hop is counted twice. Jev runs through a different vendor's endpoint entirely. Not a
    like-for-like latency comparison, and the two arms ran 24 hours apart with no serving provider
    pinned in either.
11. **The pre-registered decision rule still fails**, and fails harder here: Jev's recall on
    `unsupported` is 78.9% against the 80% bar, and the reasoning-allowed GPT-5.4 reaches 84.2%.
    The rule's second clause, "at least as good as the frontier models'", is now failed outright.
    Jev wins the hard set and loses the gate rule. Both are in the same run.

## What this changes

README weakness 1 has an answer: the hard-set gap is not an artefact of the JSON schema. It
survives giving the frontier models room to think, and survives paying between 2.4 and 4.2 times
more per claim for that room.

It does not survive being called significant on 18 items and one run. Test 4, repeats, is now the
blocker on every number in this series, not a nice-to-have.
