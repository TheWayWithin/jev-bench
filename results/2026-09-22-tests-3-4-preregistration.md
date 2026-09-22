# Pre-registration — Tests 3 and 4

Written 22 September 2026, before any Test 3 or Test 4 call was made. Committed to the repo
before the runs; the verdict quotes this file's commit hash. Nothing below changes after a result
has been seen. Anything that does change goes in the verdict as a named deviation, with the reason.

**What was already known when this was written:** every result in `results/` up to and including
Test 2 (the 20 and 21 September runs). In particular, Test 2 found the frontier models' new errors
clustered on four `supported` rows (`rz-05`, `rz-06`, `sb-04`, `sb-06`). The last sentence of the
`altered` definition below was written knowing that, and is declared here for that reason.

The code that makes every call is in `run.py` (`run_jev`, `run_jev_fanout`, `run_llm`,
`run_llm_split`, `SPLIT_LABELS`, `SPLIT_PROMPT`, `FANOUT_QUESTIONS`, `combine_fanout`) and the
plan, spend check and every statistic are in `tests34.py`, both committed with this file.

## The two questions

**Test 4.** Nothing sets a temperature or a seed on either side. Is Jev's 11-point lead on the hard
18 stable, or is it two claims of luck? Is Jev deterministic for identical input?

**Test 3.** How much of Jev's result is the question design rather than the model?

## What does not change

`BASELINE_PROMPT`, `LABELS`, `INSTRUCTIONS`, `VERDICT_SCHEMA`, the dataset and its labels, and every
existing result file. New behaviour is behind new `--arm` values (`split`, `fanout`) and a new
`--label` flag that only names the output file. The Jev schema-only call is byte-for-byte the call
of 20 September; the only addition to its output is a `served_model` field, which records the
versioned model ID the API reports as having answered.

## Systems

- Jev `jev-latest`, the alias the 20 September run used. Per TypeSafe's models page, read 22
  September 2026, it currently points to `jev-1.13.0`.
- Jev `jev-1.13.0`, the pinned version, named exactly as on that page.
- `openai/gpt-5.4`, `anthropic/claude-sonnet-5`, `google/gemini-3.1-pro-preview`, through
  OpenRouter, as on 20 September. No temperature, no seed, no provider pinned: the same as every
  earlier run.

All 42 claims every run. The easy 24 (tier B) and hard 18 (tier A) are reported separately and
never merged into one headline.

## The runs

| group | system and model | arm | runs | output label |
|---|---|---|---|---|
| Test 4 | Jev `jev-latest` | schema | 5 | `t4-r1` to `t4-r5` |
| Test 4 and 3(a) | Jev `jev-1.13.0` | schema | 5 | `t4pin-r1` to `t4pin-r5` |
| Test 4 | each of the three LLMs | schema | 5 each | `t4-r1` to `t4-r5` |
| Test 3(b) | Jev `jev-latest` | split | 5 | `t3b-r1` to `t3b-r5` |
| Test 3(b) | each of the three LLMs | split | 1 each | `t3b-r1` |
| Test 3(c) | Jev `jev-latest` | fanout | 5 | `t3c-r1` to `t3c-r5` |

38 runs, 1,596 calls. The five pinned runs serve both Test 4 (the brief asks for five on the pinned
version) and Test 3(a); they are one set of runs, not two.

Arms (b) and (c) run on `jev-latest`, so that each arm differs from its baseline, the five Test 4
`jev-latest` runs, in exactly one thing. `served_model` shows whether the alias resolved to the same
version throughout.

Calls within one system and model are made one at a time, as in every earlier run. The five
systems' queues run side by side.

## Spend

Projected from the measured per-claim cost of each system's 20 September schema-only file (the
OpenRouter `charged_usd`, and Jev's input tokens at $0.042 per million), with the split arm costed
at 1.5x and the fan-out at 4x, then 1.25x headroom on the total: **$2.90 against a $10 cap.**
`python3 tests34.py plan` prints it and needs no keys. `python3 tests34.py run` re-computes it and
stops without calling anything if it exceeds the cap.

## Scoring

Every run is scored on the original three labels. A row is right if `predicted` equals the
dataset's `label`. A failed call or an unparseable reply counts as wrong, as in `score.py`.

"Majority-of-five right" for a claim means right in at least three of the five runs. For the LLM
split arm, which is one run, it is that run's answer.

## Test 4 — repeats

Reported per system: mean, min and max accuracy across the five runs, on all 42, the easy 24 and
the hard 18; the 20 September single run alongside, for reference, not in the spread. Per claim:
how many of the five runs got it right, for every system.

**Jev determinism.** For each set of five Jev runs, count the claims where the label differs, where
the confidence differs, and where the probability distribution differs at all. If all three counts
are zero for both `jev-latest` and `jev-1.13.0`, caching a Jev verdict for identical input is safe
on this evidence. If any is non-zero, it is not, and the verdict says by how much.

**The headline, decided by this rule on the hard 18:**

- **Survives** if Jev `jev-latest`'s worst run is above every frontier model's best run.
- **Shrinks** if Jev's mean is above every frontier model's mean but the run ranges overlap.
- **Vanishes** if any frontier model's mean equals or beats Jev's.

Supporting statistic: exact two-sided McNemar on majority-of-five correctness, hard 18, Jev against
each frontier model; and the range of the five run-by-run McNemar p-values (run *i* against run
*i*). Computed by `tests34.py analyse` with `mcnemar.exact_two_sided`.

## Test 3 — three arms, run separately, never combined

### (a) Pin the version

`jev-1.13.0` against `jev-latest`, same call otherwise. Also answers whether the alias has moved
since 20 September, two ways: the `served_model` field on today's `jev-latest` runs, and a
label-by-label comparison of today's `jev-latest` against the 20 September file.

### (b) Split the compound label

`unsupported` is replaced by two options. `supported` and `not_addressed` keep their baseline text
word for word. The two new definitions, exactly as sent:

> **contradicted**: The source passage addresses what the claim asserts and says something
> incompatible with it: the opposite, a different figure, the reverse direction of an effect, or
> that the thing the claim says was done or found was not.

> **altered**: The claim is recognisably drawn from the source passage and roughly right in
> substance, but changed so that the sentence as written is not what the source says: a true
> figure attached to the wrong quantity, model, version or author; a hedge hardened into a
> certainty; a quotation assembled from separate places; or a scope wider than the passage covers.
> A shortening or paraphrase that leaves out detail but states nothing the passage does not is not
> altered: that is supported.

Both are written from the `why` records of the dataset's `unsupported` rows (`ctl-02`, `ctl-09`,
`rb-03`, `ctl-12`, `ctl-23` for contradiction; `sb-01`, `sb-02`, `sb-03`, `rb-02`, `rz-03`,
`ctl-11`, `ctl-17`, `ctl-21` for alteration). The final sentence of `altered` comes from the `why`
records of `rz-05`, `rz-06` and `sb-04` ("fair compression", "shortened but recognisable",
"materially accurate paraphrase") and is the declared exception noted at the top.

**Scoring:** `contradicted` and `altered` both map to `unsupported`. The four-way answer is kept in
`predicted_raw`. No relabelling of the dataset.

Jev gets the four options as `criteria` on the same Choice, same `INSTRUCTIONS`. Each LLM gets
`SPLIT_PROMPT`: `BASELINE_PROMPT` with the four definitions in place of the three and the JSON enum
widened to match, nothing else changed. One run per LLM, against that LLM's own five Test 4 runs.

`rz-05`, `rz-06`, `sb-04` and `sb-06` are reported by name for every system.

### (c) Multi-question fan-out

One call per claim, same state, three Noul questions, exactly as sent:

> **addresses**: A sentence from a published article makes a claim and cites a source. Does the
> source passage in `section` speak to what the claim in `claim` asserts, either way? Answer yes if
> the passage contains information that bears on whether the claim is true, even if it contradicts
> the claim. Judge only against the passage given.

> **contradicts**: A sentence from a published article makes a claim and cites a source. Does the
> source passage in `section` say something incompatible with the claim in `claim`: the opposite, a
> different figure, the reverse direction of an effect, or that the thing the claim says was done or
> found was not? Judge only against the passage given.

> **faithful**: A sentence from a published article makes a claim and cites a source. Is everything
> the claim in `claim` states either stated in the source passage in `section` or directly implied
> by it, with the same figures, attribution, version, scope and strength of wording? Leaving out
> detail is fine; adding or changing something is not. Judge only against the passage given, and do
> not credit the claim for being plausible.

**The combination rule, fixed now (`combine_fanout`, threshold 0.5):**

1. `addresses` below 0.5 → `not_addressed`.
2. Otherwise, `faithful` at or above 0.5 and `contradicts` below 0.5 → `supported`.
3. Otherwise → `unsupported`.

The rule's confidence is the joint probability of the chosen branch treating the three answers as
independent. It is recorded and never used to choose the label. Cost is reported per claim against
the single-Choice `jev-latest` runs, from the input tokens each call reports.

### What counts as "question design matters"

For each arm, against its own baseline, on all 42:

- **Question design matters** if the arm's mean accuracy falls outside the baseline's own min-to-max
  range across its five runs **and** exact McNemar on majority-of-five correctness gives p < 0.05.
- **Moved beyond run-to-run noise, not significant** if only the first holds.
- **No detectable effect** if the mean falls inside the baseline's range.

The same reading on the hard 18 is reported as secondary. The same rule applies to each LLM's one
split run against its five schema-only runs. If Jev turns out deterministic its range has zero
width, so the McNemar clause carries the whole weight; that is intended.

All three readings are publishable at the same prominence, including "no detectable effect" for
every arm, and including a Test 4 result that the headline gap is noise.

## Reproducing every number

    python3 tests34.py analyse

Needs no keys: it reads the JSONL files in `results/`. Its output is saved as
`results/2026-09-23-tests-3-4-analysis.txt` and every figure in the verdict comes from that file.
