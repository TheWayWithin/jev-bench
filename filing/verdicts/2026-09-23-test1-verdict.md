# Test 1 verdict: Jev against Claude on my triage (T-809)

> **Published 24 September 2026.** The private verdict, with every note referred to by its id
> only. Descriptions of notes (titles, topics, people, organisations) are removed and marked
> [described note removed]; every figure is unchanged. File paths below are the private
> working folder: the published runs are `filing/runs/`, the scripts `filing/code/`, and
> `python3 filing/reproduce.py` recomputes every figure here from the published runs.

> **Follow-up, 24 Sep:** Test 1b gave both models 10 retrieved filed examples; Jev rose to 83.1%, retrieval alone scored 74.7%, and the gap was not significant ("the retrieval did the work"). See `2026-09-24-test1b-verdict.md`.

**Verdict: don't.** Jev should not route my inbox, not even as triage. By the pre-registered bar
the current Claude method fails too, which is its own finding.

Pre-registration: `../test1-preregistration.md`. Scoring: `analyse.py` (written before the runs)
→ `routing-summary.json`. Description only: `describe.py` (written after the runs, changes no
verdict) → `routing-descriptive.json`. Raw runs: `routing-{jev,llm}-r{1..5}-*.jsonl`.

## What ran

- 83 filed notes, stratified by home, seed 809 (`../data/routing-key.jsonl`).
- Jev `jev-1.13.0` (every call answered by `jev-1.13.0`) and `anthropic/claude-sonnet-5` via
  OpenRouter. Five runs each, 415 calls each, 0 failed or unusable.
- All runs on 23 September 2026, 21:07 to 21:12 EDT.

## The numbers (routing-summary.json)

| | Jev | Claude Sonnet 5 |
|---|---|---|
| Agreement, mean of 5 runs | 65.3% | 76.4% |
| Agreement, range across runs | 65.1% to 66.3% | 74.7% to 78.3% |
| Agreement, majority answer | 65.1% | 77.1% |
| Sent to me (confidence below 0.80) | 43.1% | 55.4% |
| Confident answers that were wrong | 39 of 236, 16.5% | 21 of 185, 11.4% |
| Cost per item | $0.0000447 | $0.00377 |
| Items whose answer changed between runs | 2 | 6 |

Cost: Claude's per-item cost is about 84 times Jev's (0.0037669 / 0.0000447, derived from the
two figures above).

## Win, lose, or can't tell

**Jev loses.** On majority answers, Claude was right and Jev wrong on 12 notes; Jev right and
Claude wrong on 2. Exact McNemar p = 0.013. Jev is 12.0 points behind, 95% interval 3.6 to 20.5
points behind (Wald).

## The verdict rule, applied

| Clause | Jev | Claude |
|---|---|---|
| Confident answers wrong 5% or less | no, 16.5% | no, 11.4% |
| Sends half or fewer to me | yes, 43.1% | no, 55.4% |
| Not significantly worse than Claude | no | n/a |
| Cheaper | yes | n/a |
| **Result** | **don't** | **don't** (same bar) |

## Errors by kind (confusion, pooled over 5 runs, routing-summary.json)

Both models pull notes into `mission-control`. That is where most of each model's errors go.

| True home → answered mission-control | Jev | Claude |
|---|---|---|
| reference (75 answers) | 29 | 33 |
| income-bridge (75) | 25 | 20 |
| content (75) | 25 | 5 |
| knowledge (75) | 10 | 8 |

The biggest difference between the two is content: Jev sent content drafts to mission-control
25 times out of 75, Claude 5 (Claude 70 of 75 right, Jev 40). Half of Claude's lead is content:
of the 12 notes where Claude's majority answer was right and Jev's wrong, 6 are content files
(r-041, r-042, r-043, r-045, r-048, r-051; from the two `majority_right` lists in
routing-summary.json). The two going Jev's way are r-029 (income-bridge) and r-031 (books).

## Confidence, at each model's own values (routing-descriptive.json)

Neither model has a confidence level at which it made no errors.

- Jev said 1.00 on 56 answers and 10 of them were wrong (17.9%). At 0.98 and above, 118
  answers, 10 wrong (8.5%).
- Claude said 0.98 on 13 answers and 3 were wrong. At 0.90 and above, 91 answers, 10 wrong
  (11.0%).

Jev's confident errors are stable: seven of its nine confidently wrong notes were wrong at 0.80
or above in all five runs. A stable answer is not a right one, the same finding as JevBench's
`sb-03`.

## The confident errors, and the labels

Jev, confidently wrong (note: filed in → answered, runs out of 5): r-003 (mission-control →
efformism, 1); r-020 (income-bridge → content, 5); r-042, r-046 and r-051 (content →
mission-control, 5 each); r-062 (knowledge → mission-control, 5); r-076, r-079 and r-080
(reference → mission-control, 3, 5, 5).

Claude, confidently wrong: r-003 (mission-control → efformism, 5); r-034 (books → delete, 5);
r-071, 149 characters (reference → delete, 3); r-074 (reference → mission-control, 3); r-080
(reference → mission-control, 5).

My reading, which is a judgement and changes nothing above: several of these are arguable labels,
not clear model errors. r-003, r-074 and r-071 (the 149-character one) are the kind of item where
the folder is a convention rather than the obvious answer. [Described note removed: what each of
the three is.] The labels were fixed before the runs and are not changed after (checklist step
8). What it does show is that my own filing has a mission-control-shaped blur in it, and both
models found it.

## Deviations from the pre-registration

1. **Approval.** Jamie's reply at 21:07 EDT was "continue and complete the task", taken as the
   yes to the pre-registration.
2. **The ideas key was not run.** Jamie did not mark the 40 ideas, and his decisions can't be
   invented. The queue is untouched. The pre-registration makes routing the deciding key, so the
   verdict stands on routing alone; the ideas half is owed if he marks them later
   (`data/ideas-items.jsonl`, `test1.py run --task ideas`).
3. **`describe.py` was written after the runs**, as description only. It does not touch the
   0.80 line or the verdict.

## What this can't show

As pre-registered: labels chosen mostly by Claude sessions and accepted by Jamie (favours the
Claude arm); a balanced sample, not the real inbox mix; notes as they are now, not as they
arrived; books and Efformism at four notes each; one short window on one day; one question
shape, not TypeSafe's recommended several narrow questions.
