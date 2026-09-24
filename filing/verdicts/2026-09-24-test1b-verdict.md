# Test 1b verdict: does Jev need labelled examples to file my notes? (T-818)

> **Published 24 September 2026.** The private verdict, with every note referred to by its id
> only. Descriptions of notes (titles, topics, people, organisations) are removed and marked
> [described note removed]; every figure is unchanged. File paths below are the private
> working folder. The pool, the neighbour lists and the notes cannot be published, so "How to
> rerun" below needs the private files; publicly, `python3 filing/reproduce.py` recomputes every
> figure here from `filing/runs/` and the reduced neighbour list in `filing/data/`, and
> `filing/data/frozen-facts.json` carries the full sha256 of every frozen file.

> **Follow-up, 24 Sep:** Test 1c, on 75 fresh notes: Jev keeping its sure answers and passing the rest to Claude matched Claude exactly (86.7%) at 37% of the cost; yes/no questions per folder and rewording showed no significant gain; retrieval again not beaten. See `2026-09-24-test1c-verdict.md`.

**Verdict rule outcome: "The retrieval did the work."** Jev with ten retrieved examples (arm B)
did not significantly beat the retrieval it was given (arm C): p = 0.19. The other two outcomes
did not hold. "Jev with examples earns its place" needs B to beat C, and it didn't. "Jev still
loses with examples" needs B to be significantly worse than Sonnet 5 with the same examples (arm
D), and it wasn't: p = 0.0625.

**Test 1's bar: don't, for both.** Jev with examples had 15 of 275 confident answers wrong
(5.5%); Sonnet 5 with examples had 16 of 297 (5.4%). The bar is 5%.

What the rule's label does and doesn't say: "the retrieval did the work" is the pre-registered
name for "B did not significantly beat C". It does not mean Jev added nothing. Jev was ahead of
retrieval on 14 notes and behind on 7, 8.4 points ahead, and the 95% interval (-2.2 to +19.1
points) covers both no gain and a large one. 83 notes can't separate them.

Pre-registration: `../test1b-preregistration.md` (unchanged). Scoring: `../analyse1b.py` →
`test1b-summary.json`. Raw runs: `test1b-{B,D}-r{1..5}-*.jsonl`, `test1b-C-r1-*.jsonl`; arms A and
E reuse Test 1's `routing-{jev,llm}-r{1..5}-*.jsonl`. Examples: `../data/test1b-neighbours.jsonl`,
built from the frozen pool `../data/test1b-pool.jsonl` by `../test1b_neighbours.py`, checked by
`../check_test1b_neighbours.py` (exits 0).

## How to rerun

From `tools/jev-stack-tests/`:

1. `python3 check_test1b_neighbours.py`: rebuilds the neighbours from the frozen pool twice and
   compares them byte for byte with the saved file; checks 83 notes, exactly 10 neighbours each,
   none its own.
2. `python3 analyse1b.py`: validates every run file (83 rows, a usable answer, the served model
   logged and equal to the pinned model), then regenerates `test1b-summary.json` from the raw runs.
3. New model runs, if wanted: `../jev-bench/.venv/bin/python test1b.py run --arm B --label r6`
   (arms B, C, D). Arm C needs no key and reproduces exactly. `analyse1b.py` refuses to score
   anything but the pre-registered run counts (5, 1, 5), so move an extra run out of `results/`
   before scoring, or compare it by hand.

## What ran

- The same 83 notes and labels as Test 1 (`../data/routing-key.jsonl`), the same eight options and
  wording. The only change to the instructions: one sentence, "`examples` are similar notes
  already filed in this vault, each with the home it was filed to."
- Examples: BM25 (k1 = 1.5, b = 0.75), lower-cased word tokens, title plus first 1,500 characters,
  k = 10, leave one out. Each shown as title, first 500 characters and home, highest score first.
  Identical for every arm and run.
- Pool: 605 notes (books 4, content 103, efformism 4, income-bridge 82, knowledge 253,
  mission-control 86, reference 73), sha256 `e67cb9ba…b5c3`. Neighbours file sha256
  `e7f58386…3aaf`. 509 of the 830 neighbour slots (61.3%) carry the test note's own label.
- Jev `jev-1.13.0` (every call served by `jev-1.13.0`); `anthropic/claude-sonnet-5` via OpenRouter
  (every call served by `anthropic/claude-sonnet-5`). Five runs each of B and D, 415 calls each,
  0 failed or unusable. Arm C one deterministic run.
- All runs on 24 September 2026, 15:47 to 15:53 EDT.

## The numbers (test1b-summary.json)

| | A: Jev | B: Jev + examples | C: retrieval only | D: Sonnet 5 + examples | E: Sonnet 5 |
|---|---|---|---|---|---|
| Agreement, mean of runs | 65.3% | 83.1% | 74.7% | 88.0% | 76.4% |
| Range across runs | 65.1% to 66.3% | 83.1% to 83.1% | one run | 85.5% to 89.2% | 74.7% to 78.3% |
| Majority answer | 65.1% | 83.1% | 74.7% | 89.2% | 77.1% |
| Sent to me (below 0.80) | 43.1% | 33.7% | n/a | 28.4% | 55.4% |
| Confident answers wrong | 39 of 236, 16.5% | 15 of 275, 5.5% | n/a | 16 of 297, 5.4% | 21 of 185, 11.4% |
| Cost per item | $0.0000447 | $0.000119 | $0 | $0.00906 | $0.00377 |
| Items whose answer changed | 2 | 0 | 0 | 6 | 6 |

Costs: Jev from the price table (input tokens × $0.042 per million); Claude is OpenRouter's
reported charge; retrieval makes no call. With examples, Claude costs about 76 times Jev per item
(0.0090594 / 0.0001192, derived from the two unrounded figures in the summary).

## The comparisons (exact McNemar, two-sided, majority answers, 83 notes)

| | First right, second wrong | Second right, first wrong | p | Difference, 95% Wald |
|---|---|---|---|---|
| **Main: B vs C** | 14 | 7 | 0.189 | B +8.4 points (-2.2 to +19.1) |
| **Second: B vs D** | 0 | 5 | 0.0625 | B -6.0 points (-11.1 to -0.9) |
| B vs A (reported) | 18 | 3 | 0.0015 | B +18.1 points (+8.0 to +28.2) |
| D vs E (reported) | 11 | 1 | 0.0063 | D +12.0 points (+4.3 to +19.8) |
| C vs A (reported) | 20 | 12 | 0.215 | C +9.6 points (-3.6 to +22.8) |

B against D: the Wald interval excludes zero while the exact test does not reach 5%. The exact test
is the pre-registered one; the Wald interval is the rough guide Test 1 also printed. With 5
discordant notes, all one way, the exact p cannot go below 0.0625.

The reported comparisons are description, not results. They say examples lifted both models, by
a margin the exact test can see: Jev by 18 notes to 3, Claude by 11 to 1.

## The verdict rule, applied

| Clause | Result |
|---|---|
| B significantly beats C | no (p = 0.189) |
| B significantly worse than D | no (p = 0.0625) |
| "Jev with examples earns its place" (both) | **does not hold** |
| "The retrieval did the work" (B does not beat C) | **holds** |
| "Jev still loses with examples" (B worse than D) | **does not hold** |

Test 1's bar:

| Clause | B: Jev + examples | D: Sonnet 5 + examples |
|---|---|---|
| Confident answers wrong 5% or less | no, 5.5% | no, 5.4% |
| Sends half or fewer to me | yes, 33.7% | yes, 28.4% |
| Not significantly worse than the other | yes | yes |
| Cheaper | yes | no |
| **Result** | **don't** | **don't** |

Test 1 applied its bar to Claude without the "cheaper" clause. Read that way, D is still "don't",
because the confident-error clause fails first.

## Near-duplicates

**4 of the 83 test notes have a near-duplicate among their ten neighbours**: r-029 (Jaccard
0.78), r-047 and r-048 (each other's neighbour, 0.70), r-042 (0.61). [Described note removed:
what each pair is.] All four near-duplicates carry the same home as the test note. B, C and D
got all four right.

Leaving the four out changes no count in either tested comparison: B vs C is still 14 to 7 (p =
0.189) on 79 notes, and B vs D is still 0 to 5 (p = 0.0625) (`descriptive_without_near_duplicates`).

## Where the arms differ (from the majority_right lists and the key)

- **Where Jev beat retrieval (14 notes):** reference 4, mission-control 3, efformism 3, content 3,
  books 1. Efformism and books have 4 notes each in the whole pool, so a vote over ten neighbours is
  outnumbered by other homes. Retrieval got 1 of 4 efformism notes; Jev with examples got all 4.
- **Where retrieval beat Jev (7 notes):** reference 3, income-bridge 2, knowledge 2.
- **Where Claude beat Jev with the same examples (5 notes):** r-020, r-022 (income-bridge), r-033
  (books), r-062, r-063 (knowledge). Jev beat Claude on none.
- **What examples did for Jev (18 notes gained):** content 6, income-bridge 5, reference 4, one
  each of efformism, mission-control, knowledge. Content drafts were Test 1's biggest gap: Jev
  with examples filed content right 70 times in 75 (Test 1: 40).
- **Stability:** Jev with examples gave the same answer to every note in all five runs.
- **Confident errors, B:** r-003 (the arguable label from Test 1), r-046, r-080. D's: the same
  three plus r-034. [Described note removed: what each is.]
- **Answers at confidence 1.00:** Jev with examples, 20 answers, 5 wrong (Test 1: 56, 10 wrong).
- **Arm C ties:** 5 notes had a tied vote, broken by summed score as pre-registered (r-007, r-020,
  r-036, r-044, r-047).

## Cost of the runs

Arm B, 415 calls: $0.049 (price table). Arm D, 415 calls: $3.76 (OpenRouter's charge). Arm C: $0.
One unscored smoke call: $0.00012. Total about $3.81.

## Deviations and choices the pre-registration left open

Each was made before any scored call unless it says otherwise.

1. **Approval.** Jamie launched the goal that runs it, which the pre-registration names as its
   approval.
2. **The pool is 605 notes, not 597.** The vault gained 8 eligible notes between 23 and 24 Sep (7
   knowledge, 1 content). The pre-registration's "597" describes 23 Sep; the rule it states is
   "every eligible note". The pool was frozen to `data/test1b-pool.jsonl` so the neighbours can be
   rebuilt exactly. Pool notes are read as they are on disk today; test notes keep their 23 Sep text
   as queries. No test note had moved, so leave-one-out by path excludes every one.
3. **BM25 details not fixed in the pre-registration:** idf = ln((N − df + 0.5)/(df + 0.5) + 1),
   N the whole pool; each distinct query term counted once; ranking ties broken by path; document
   and query text are the title and the 1,500 characters joined by a newline.
4. **Near-duplicate definition** (the pre-registration asks for a count, not a method): Jaccard
   similarity of word-token sets, at least 0.5. First set at 0.8, which counted none although two
   versions of one note scored 0.70. Moved to 0.5 after reading the similarity values and before
   any model call; the top values run 0.78, 0.70, 0.70, 0.61, then 0.40.
5. **One smoke call** (Jev with examples, key note r-001) before the scored runs, to confirm Jev
   accepts a list in state. Not scored, not in `results/`.
6. **Arms B and D run 1 ran at the same time**; the other runs one after another.
7. **Test 1's bar for D** is reported both ways (with and without "cheaper"); both give "don't".

## Independent check (24 Sep)

A fresh sub-agent that wrote none of this reran both scripts (exit 0), recounted every tested
figure from the raw run files, and checked the method against the pre-registration. It found no
wrong figure in this file and no undeclared departure. Two nits here were fixed (the description
of the r-029 pair; the rerun note on run counts). In the article it found one wrong number
(five-run averages "within a point": Claude with examples is 1.2 points off) and several
overstatements (the rule's label read as "the search did the work"; "nearly as well" on the hero;
a books-folder loss left out; an untraceable inbox claim). All were fixed before the article was
left held.

## What this can't show

Everything Test 1 couldn't: labels chosen mostly by Claude sessions and accepted by Jamie; a
balanced sample, not the real inbox; notes as they are now; one day. Plus, as pre-registered:
k = 10 is one choice, not a sweep, and 83 notes are too few to separate an 8-point gain from none.
The examples come from the same vault the labels do, so a note filed by the same convention as its
neighbours is easy for every arm with examples.
