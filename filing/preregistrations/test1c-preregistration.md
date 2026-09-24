# Test 1c pre-registration: does Jev know when it doesn't know, and can better questions help? (T-821)

> **Published 24 September 2026**, after all three tests had run. This is the
> pre-registration as approved; nothing in it needed redacting. Its last lines say nothing
> goes into the public jev-bench repo: that was the plan when it was written, changed so
> the numbers behind the article can be checked. Paths such as `data/` and `results/` are
> the private working folder; the published copies are `filing/data/` (reduced, no note
> text) and `filing/runs/`, and the scripts are in `filing/code/`. The frozen question file
> is published with two passages of its change log withheld, so it no longer hashes to the sha256 recorded
> for it; `filing/data/frozen-facts.json` has the recorded hash.

Written 24 September 2026, before any Test 1c call and before the held-out notes are drawn.
Jamie approves it by saying so. Nothing below changes after approval; any deviation goes in the
verdict file, dated, with the reason.

## Why this test exists

Test 1b (`results/2026-09-24-test1b-verdict.md`) showed that ten retrieved examples lifted Jev from
65% to 83.1%, that a keyword search over the same examples scored 74.7% (not significantly
different), and that Sonnet 5 with the same examples scored 89.2% (not significantly different
either).

Three questions were left open, and this test answers them on notes nobody has looked at yet:

1. **Escalation.** Jev is meant to answer when it is sure and pass the rest on. Working it out
   after the Test 1b runs, Jev keeping its 80%-sure answers and passing the rest to Claude matched
   Claude's accuracy (88.0%) at about 40% of Claude's cost. That was worked out after the event, on
   notes already studied. This test fixes the rule first and scores it on fresh notes.
2. **Question shape.** TypeSafe recommends several narrow questions over one broad one. Test 1b
   asked one eight-way question. This test adds one yes/no question per folder.
3. **Improvement.** Jev can't be retrained; the wording of the questions is the lever. This test
   allows one bounded round of rewording on notes already used, then scores the result once on
   the fresh notes.

## What stays the same as Test 1b

- The frozen pool `data/test1b-pool.jsonl` (605 notes, sha256 `e67cb9ba…b5c3`), its folder labels,
  and the retrieval: BM25 (k1 = 1.5, b = 0.75), `test1b_neighbours.py`'s tokens and idf, k = 10,
  leave one out, each example shown as title, first 500 characters and home.
- The eight options and their wording (`ROUTING_OPTIONS` in `test1.py`), and the note text (title
  plus first 1,500 characters, frontmatter stripped).
- Jev pinned to `jev-1.13.0`; Claude `anthropic/claude-sonnet-5` via OpenRouter, temperature not
  set, max 1,500 tokens, no reasoning step. Five runs per model arm.
- The keep line **0.80** and the confident-error bar **5%**. Not tuned.

## The two sets of notes

- **Working set (W):** the 83 Test 1 notes and their Test 1b examples. Already seen and studied,
  so they are used only for the rewording round. Nothing scored on W is a result.
- **Held-out set (H):** drawn once from the frozen pool, excluding all 83 W notes: 15 notes from
  each home, seed 821, the same stratified draw as `build_keys.py`. The books and efformism homes
  have no unused notes (all four of each are in W), so H covers the other five homes: **75 notes**.
  All eight options are still offered. Neighbours for H are built from the same pool, leave one
  out, and saved to `data/test1c-heldout.jsonl` and `data/test1c-neighbours.jsonl`, with their
  sha256 hashes recorded, before any call is made. `check_test1b_neighbours.py`'s checks
  (exactly 10, none its own, rebuild identical) are run on them and must exit 0.
- **No model call is made on H until the reworded question set is frozen** (below).

## The arms, all scored on H, all with the same 10 examples

| Arm | What it is | Runs |
|---|---|---|
| C | Retrieval only: majority home of the 10, ties to the higher summed score (as Test 1b) | 1 |
| B | Jev, one eight-way Choice question (as Test 1b) | 5 |
| D | Sonnet 5, as Test 1b | 5 |
| F | **Jev, one yes/no question per home**: eight Nouls in one call, same state. Each Noul's instructions: "Should this note be filed to `<home>`? " followed by that home's `ROUTING_OPTIONS` text, after the Test 1b instructions. Answer: the home with the highest value (ties to the order of `ROUTING_OPTIONS`) | 5 |
| G | **Jev with the reworded questions**, in whichever shape (B or F) did better on W after rewording | 5 |

**Confidence, for keeping or passing on.** B and G-as-Choice: Jev's reported confidence, as in
Test 1. F and G-as-Nouls: keep only if the top value is at least 0.80 **and** the second-highest is
below 0.50. A note that fits two homes is passed on.

**Escalation arms, computed from the runs above, no new calls.** For each Jev arm (B, F, G), run *i*
is paired with D's run *i*:

- **Jev → Claude:** Jev's answer where Jev keeps it, D's answer otherwise.
- **Jev → me:** Jev's answer where Jev keeps it; the rest counted as sent to Jamie.
- Cost per note for Jev → Claude: Jev's cost on every note plus D's cost on the notes passed on.

## The rewording round (on W only)

- **What may change:** the instruction sentence and the eight home descriptions, and only in wording.
  Not the examples, k, the model, the 0.80 line, the keep rule or the combining rule.
- **Where wording may come from:** `BRAIN-SCHEMA.md`'s homes and filing rules. Every changed
  sentence cites the rule it comes from. **No wording may name or quote a W note**, its title or a
  term used only in it, so the change is about the rules, not those 83 notes.
- **How:** start from Test 1b's B runs and a first F run on W. List W's errors. Reword. Run once on
  W. At most **three rounds**. The final wording and shape (B or F) is the one with the higher W
  majority agreement; ties go to the fewer changed words. It is saved to `test1c-questions.json`
  with its sha256 in the verdict before any call on H.
- **Labels are not changed.** Errors where the label looks arguable are listed for Jamie in the
  verdict, not relabelled.
- Only Jev is reworded. Claude keeps Test 1b's wording. This is deliberate: the question is
  whether Jev's lever works. Stated as a limit.

## Metrics

As Test 1b for every arm: agreement per run and its range, majority answer (3 of 5; none counts
as wrong), share passed on, confident answers that were wrong, cost per note, notes whose answer
changed, confusion table. For the escalation arms: majority agreement, share passed on, and cost
per note. Near-duplicate count for H, with the Test 1b definition (Jaccard ≥ 0.5).

## The comparisons, fixed now

Exact McNemar, two-sided, on majority answers over the 75 H notes. Four tests, so **Holm's
correction** is applied across them at 5%; unadjusted p-values are also reported.

1. **Escalation: Jev → Claude (from B) against D.** Reported with the difference and its 95% range.
2. **Question shape: F against B.**
3. **Rewording: G against B.** Does the improvement carry over to notes it never saw?
4. **Replication: B against C.** Does Test 1b's main result repeat on fresh notes?

## The verdict rule

- **"Escalation pays"** if Jev → Claude is not significantly worse than D **and** costs no more than
  half of D per note. A non-significant difference on 75 notes is not proof they are equal; the
  verdict says how large a gap the 95% range still allows.
- **"Narrow questions help" / "hurt"** if F is significantly better / worse than B; otherwise "no
  difference shown".
- **"Rewording carried over"** if G is significantly better than B; "did not carry over" otherwise.
  If G's W score rose but its H score did not, say so plainly: that is the overfitting the
  held-out set exists to catch.
- **Replication:** "retrieval did the work again" if B does not significantly beat C.
- **Test 1's bar**, applied to Jev → me for B, F and G: confident answers wrong at most 5%, at most
  half sent to Jamie. Use it / triage only / don't.

## Cost

Estimate from Test 1b: D on 75 notes, 5 runs, about $3.40. Jev arms and the rewording rounds under
$0.50. **Cap: $10.** If spend passes the cap, stop and report what ran.

## What it can't show

Everything Test 1b couldn't: labels chosen mostly by Claude sessions and accepted by Jamie; a balanced
sample, not the real inbox; notes as they are now; one or two days. Plus: H has no books or
efformism notes, the two homes where Test 1b's arms differed most; Claude is not reworded; one
rewording round of at most three steps is one attempt, not a method; the escalation is to Sonnet 5
without reasoning, and no reasoning model is tested.

## Where results go

`results/test1c-*` for raw runs (W rounds as `test1c-W-*`, H arms as `test1c-{B,C,D,F,G}-*`), a
summary JSON regenerated by one command, and `results/2026-09-2X-test1c-verdict.md`. A one-line
pointer from the Test 1b verdict. Nothing goes into the public jev-bench repo. The held filing
article is rewritten around the verdict only after the verdict is written and independently
checked.
