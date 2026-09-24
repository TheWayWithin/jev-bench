# Test 1 pre-registration: Jev against Claude on my triage (T-809)

> **Published 24 September 2026**, after all three tests had run. This is the
> pre-registration as approved; nothing in it needed redacting. Its last line says nothing
> goes into the public jev-bench repo: that was the plan when it was written, changed so
> the numbers behind the article can be checked. Paths such as `data/` and `results/` are
> the private working folder; the published copies are `filing/data/` (reduced, no note
> text) and `filing/runs/`, and the scripts are in `filing/code/`.

Written 23 September 2026, before any scored run. Once Jamie says yes, nothing in this file
changes. Any later deviation goes in the verdict file, dated, with the reason.

## The question

Can Jev (TypeSafe's typed-decision model) do my triage as well as the method I use now, where
Claude proposes and I decide? Two jobs, each a closed choice about a piece of text:

1. **Routing**: which home in the vault a note belongs in (the main test).
2. **Ideas**: yes, no or not now on a proposed action from the ideas queue (the second test).

## The two answer keys

**Routing: 83 notes, labelled by the folder each one ended up in.**

The plan was notes that went through the inbox. That record doesn't exist: the vault's git
ignores `0-Inbox/`, so no move was ever recorded, and the 93 filed notes that carry a capture
stamp are nearly all in `knowledge/`, most of them YouTube notes. On that key, answering
"knowledge" every time would score over 90%. It would measure the commonest answer, not routing.

So the key is a **stratified sample**: up to 15 notes from each home, drawn at random with a
fixed seed (809) by `build_keys.py`, so anyone can redraw it and get the same 83.

| Home | Notes in the home | Drawn |
|---|---|---|
| mission-control (projects and products) | 86 | 15 |
| income-bridge | 82 | 15 |
| content (ideas, drafts, published; article files only) | 102 | 15 |
| knowledge (excluding the Readwise sync) | 246 | 15 |
| reference | 73 | 15 |
| books | 4 | 4 |
| efformism | 4 | 4 |
| **Total** | | **83** |

Dates: 18 February to 23 September 2026 (25 dated by filename, the rest by file date).
`data/routing-key-summary.json` holds these figures.

What each model sees: the note's title and the first 1,500 characters of its text, with the
frontmatter removed (lines like `type: book-note` are written at filing time and give the
answer away). Eight options, worded from BRAIN-SCHEMA.md's homes and filing decision:
mission-control, income-bridge, books, efformism, content, knowledge, reference, delete.
`delete` is offered because the schema offers it. No note in the key carries it.

**Ideas: the 40 open rows of the ideas queue, labelled by Jamie.** Jamie marks each yes, no
or not now in one pass, **before any model runs**, and never sees a model's answer first.
His answers are recorded with `mc-candidate.py`, which clears the queue as a side effect.
Both models get the same short description of Jamie and his five priorities, fixed in
`test1.py` before any run.

## The two systems

| | Jev | Claude |
|---|---|---|
| Model | `jev-1.13.0`, pinned; the version that answered is logged | `anthropic/claude-sonnet-5` via OpenRouter |
| Question | one Choice per item, options as above | same item, same options, JSON answer plus confidence |
| Settings | none exposed | temperature not set (provider default), max 1,500 tokens, no reasoning step |
| Confidence | Jev's probability for its answer | Sonnet's stated probability that its answer is the one Jamie would give |
| Cost | input tokens × $0.042 per million (TypeSafe's price, read 20 Sep) | OpenRouter's reported charge |

**Five runs per model per task**, same items, same prompt. All on 23 to 24 September.

## What gets measured

- **Agreement**: share of items where the answer matches the label. A failed call or unusable
  reply counts as wrong. Reported for every run, then the mean and the range.
- **Majority answer**: for each item, the answer given in at least 3 of 5 runs. No such answer
  counts as wrong.
- **Escalated share**: share of answers with confidence below the threshold.
- **Errors at high confidence**: wrong answers at or above the threshold, divided by all answers
  at or above it, pooled over the five runs. Per-run range beside it.
- **Cost per item**: mean cost of one call.
- **Run-to-run spread**: range of per-run agreement, and the number of items whose answer
  changed between runs.
- **Errors by kind**: a confusion table, label against answer, pooled over runs.

## The escalation rule, fixed now

**An answer with confidence below 0.80 goes to Jamie. At 0.80 or above, it is acted on.**

The same 0.80 for both systems. It is not tuned after the runs. The risk-coverage curve at
each model's own confidence values will be shown as a description, never used to move the line.

## Win, lose, or can't tell

The main comparison is **routing agreement, Jev against Claude**, on the majority answers,
using the exact McNemar test (two-sided, 5%) on the items where one was right and the other
wrong.

- **Jev wins**: significant, in Jev's favour.
- **Jev loses**: significant, in Claude's favour.
- **Can't tell them apart**: anything else. The write-up won't call this a tie. It will say
  how big a gap the test could have missed (95% interval on the difference).

With 83 items one item is worth 1.2 points. With fewer than six disagreements the test cannot
come out significant, whatever the split.

## The verdict rule

Decided on routing. Ideas is reported beside it and any conflict is stated, but it does not
change the verdict.

- **Use Jev**: its errors at high confidence are 5% or fewer, it escalates half the items or
  fewer, it is not significantly worse than Claude on agreement, and it is cheaper per item.
- **Use it as triage only**: errors at high confidence are 5% or fewer, but it escalates more
  than half, or it is significantly worse than Claude. Its confident answers can be trusted;
  it can't carry the job.
- **Don't**: errors at high confidence above 5%, or no answer reaches 0.80.

The same bar is applied to Claude, so the write-up can say whether the current method passes it.

## What this test can't show

- **Who set the labels.** A note's folder was mostly chosen by a Claude session and accepted by
  Jamie, not chosen by Jamie blind. That probably favours the Claude arm, which is the same
  family of model. There is no second labeller.
- **The real inbox mix.** The sample is balanced on purpose. The real inbox is mostly learning
  material, so real-world agreement will differ from the figure here, most likely upwards.
- **Notes as they arrived.** The models see notes as they are now, after filing and editing.
- **Rare homes.** Books and Efformism have four notes each. Nothing about those two can be
  read on its own.
- **Other days.** All runs fall in one short window.
- **Other question shapes.** TypeSafe recommends several narrow questions per call. This test
  asks one, as the task specifies.
- **"As good as".** No equivalence margin is set and 83 items couldn't show one. If the result
  is "can't tell them apart", that is all it is.
- **Ideas beyond one evening.** Jamie's yes, no and not now are one evening's decisions.

## Files

`build_keys.py` builds both keys. `test1.py` runs them. `analyse.py` scores them against this
file. Raw runs and the verdict go to `results/`. Nothing goes into the public jev-bench repo.
