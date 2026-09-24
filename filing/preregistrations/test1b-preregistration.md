# Test 1b pre-registration: does Jev need labelled examples to file my notes? (T-818)

> **Published 24 September 2026**, after all three tests had run. This is the
> pre-registration as approved, except one note's path, marked [redacted]. Its last line
> says nothing goes into the public jev-bench repo: that was the plan when it was written,
> changed so the numbers behind the article can be checked. Paths such as `data/` and
> `results/` are the private working folder; the published copies are `filing/data/`
> (reduced, no note text) and `filing/runs/`, and the scripts are in `filing/code/`.

Written 24 September 2026, before any Test 1b run. Jamie approves it by launching the goal that
runs it. Nothing below changes after the first scored call; any deviation goes in the verdict
file, dated, with the reason.

## Why this test exists

Test 1 (23 Sep, `test1-preregistration.md`, `results/2026-09-23-test1-verdict.md`) gave both
models a note and eight folder names and nothing else. Jev lost: 65.3% agreement against Claude
Sonnet 5's 76.4%, p = 0.013, and 16.5% of its confident answers were wrong.

The sector research filed 24 Sep ([redacted: the path of a research note in the vault]) says that
was the wrong setup. The strongest independent routing result for Jev (BANKING77, 92.4%) gave it 24
retrieved labelled examples per prediction, and its author says they did not measure a
retrieval-only classifier, so nobody knows how much of the score was Jev and how much was the
retrieval. This test answers both questions on my own notes.

## What stays the same as Test 1

- The same 83 notes: `data/routing-key.jsonl`, labels unchanged.
- The same eight options and wording (`ROUTING_OPTIONS`, `ROUTING_INSTRUCTIONS` in `test1.py`),
  the same note text (title plus first 1,500 characters, frontmatter stripped).
- Jev pinned to `jev-1.13.0`; Claude is `anthropic/claude-sonnet-5` via OpenRouter, temperature
  not set, max 1,500 tokens, no reasoning step.
- The escalation line: **0.80**. The confident-error bar: **5%**. Not tuned.

## The examples

- **Pool:** every note eligible under `build_keys.py`'s rules across the seven homes (597 notes
  on 23 Sep), with its home as its label. **Leave one out:** a note is never its own example.
  Other test notes may be examples for each other, as they would be in a real vault.
- **Retrieval:** BM25 (k1 = 1.5, b = 0.75), lower-cased word tokens, over each pool note's title
  plus first 1,500 characters, queried with the test note's title plus first 1,500 characters.
  Deterministic, standard library only.
- **k = 10** neighbours. Each example is shown as its title, its first 500 characters, and the home
  it was filed to, highest score first.
- The examples are identical for every arm and every run. Save them to
  `data/test1b-neighbours.jsonl` before any model is called.

## The arms

| Arm | What it is | Runs |
|---|---|---|
| A | Jev, no examples | reuse the five 23 Sep runs, no new calls |
| B | **Jev with the 10 examples** in state, one Choice question | 5 |
| C | **Retrieval only**: the most common home among the 10 neighbours; ties go to the home with the higher summed BM25 score. No model | 1 (deterministic) |
| D | **Sonnet 5 with the same 10 examples** in the prompt | 5 |
| E | Sonnet 5, no examples | reuse the five 23 Sep runs |

The only change from Test 1's instructions: one added sentence saying `examples` are similar notes
already filed in this vault, each with the home it was filed to.

## Metrics

Exactly as Test 1: agreement per run and its range, majority answer (3 of 5; none counts as wrong),
share escalated, confident answers that were wrong, cost per item, items whose answer changed,
confusion table. For arm C, one run is the majority answer and there is no confidence, so it has
no escalation or confident-error figure.

## The comparisons, fixed now

Both use the exact McNemar test, two-sided, on majority answers, at 5%.

1. **Main: B against C.** Does Jev add anything over the retrieval it is given?
2. **Second: B against D.** With the same examples, is Jev still behind Claude?

Reported but not tested as results: B against A (what examples do for Jev), D against E (what
they do for Claude), C against A.

## The verdict rule

- **"Jev with examples earns its place"** only if B significantly beats C **and** B is not
  significantly worse than D. Both must hold. Requiring both is stricter than either alone, so no
  correction for two tests is applied.
- **"The retrieval did the work"** if B does not significantly beat C.
- **"Jev still loses with examples"** if B is significantly worse than D.
- Separately, Test 1's bar applied to B and D: use it / triage only / don't (confident answers
  wrong at most 5%, at most half sent to me, not significantly worse than the other, cheaper).

## What it can't show

Everything Test 1 couldn't (labels mostly chosen by Claude sessions and accepted by Jamie, a
balanced sample, notes as they are now, one day). Plus: near-duplicate notes in the pool (for
example two versions of one draft) can hand an arm the answer; count how many test notes have a
near-duplicate among their neighbours and report it. k = 10 is one choice, not a sweep.

## Where results go

`results/test1b-*` for raw runs, a summary JSON, and `results/2026-09-24-test1b-verdict.md`. A
one-line pointer from `results/2026-09-23-test1-verdict.md` to the new verdict. Nothing goes into the
public jev-bench repo.
