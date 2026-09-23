# Verdict, Tests 3 and 4 — ask Jev properly, then find out how much is noise

**The questions.** Test 4: nothing sets a temperature or a seed on either side, so is Jev's
11-point lead on the hard 18 stable, or two claims of luck? Is Jev deterministic for identical
input? Test 3: how much of Jev's result is the question design rather than the model?

**The answer to Test 4: the lead shrinks.** Over five runs each, Jev's lead on the hard 18 over the
best frontier model falls from 11.1 points to 3.3: 73.3% against GPT-5.4's 70.0%, on means. Jev
still has the highest mean of the four, but its worst run, 72.2%, is the same as the best run of
GPT-5.4 and of Sonnet 5, and no gap against any of them is significant. Gemini 3.1 Pro never got
above 66.7%. The 20 September single run caught Jev at the top of its own range: 77.8% on the hard
18, which it matched in one of today's five runs. The other four scored 72.2%.

_Corrected 2026-09-23: this paragraph originally said Jev's worst run matched the best run of every
frontier model. Gemini 3.1 Pro's best hard-18 run is 66.7% (run by run: 66.7, 61.1, 66.7, 55.6,
66.7); only GPT-5.4 and Sonnet 5 reach 72.2%. The same error is corrected under "The headline"
below. Caught by outside review of the downstream article._

**Jev is not deterministic.** Across five identical calls per claim, the confidence changed on 28
of 42 claims and the label on 2. Every label that flipped had a confidence below 0.47 on every
run. So caching a verdict for identical input is not safe in general; no claim with a confidence
of 0.5 or more on any run changed label, in 420 schema-only calls across both model names.

**The answer to Test 3: none of the three changes helped Jev.** Pinning the version changed
nothing, because the alias and the pin are the same model today. Splitting the compound label cost
Jev 1.4 points on all 42, and offering the same split to the three frontier models moved none of
them outside their own run-to-run spread. The multi-question fan-out TypeSafe recommends cost the
same as the single question to within 4% and scored 6.2 points lower. It is the largest move in
either test, and still not significant: p = 0.219.

**So on this set, how the question was asked did not explain Jev's result, and the result was
smaller than one run made it look.** Both are findings, and both carry the same weight here.

Runs made 22 September 2026, 18:29 to 18:48 EDT, 42 claims each, 38 runs, 1,596 calls, no failed
calls, no unparseable replies. Pre-registered in `results/2026-09-22-tests-3-4-preregistration.md`,
committed as `b4a7ce5` at 18:29:29, 30 seconds before the first call. No deviations from it.

Every number below is in `results/2026-09-23-tests-3-4-analysis.txt`, which is the output of
`python3 tests34.py analyse`. That command needs no keys and reads the 38 JSONL files in
`results/` whose names carry `t4-`, `t4pin-`, `t3b-` or `t3c-`. The standard per-run scoring of
all 38 by `score.py` is in `results/2026-09-23-tests-3-4-scored.txt`.

## The numbers: Test 4, five runs each, schema-only

| | all 42, mean (range) | the easy 24 | the hard 18 | hard 18, 20 Sep single run |
|---|---|---|---|---|
| **Jev** `jev-latest` | 83.8% (83.3–85.7) | 91.7% every run | **73.3%** (72.2–77.8) | 77.8% |
| **Jev** `jev-1.13.0` | 84.8% (83.3–85.7) | 91.7% every run | **75.6%** (72.2–77.8) | not run |
| GPT-5.4 | 87.1% (85.7–88.1) | 100% every run | 70.0% (66.7–72.2) | 66.7% |
| Sonnet 5 | 85.7% (83.3–88.1) | 100% every run | 66.7% (61.1–72.2) | 66.7% |
| Gemini 3.1 Pro | 84.3% (81.0–85.7) | 100% every run | 63.3% (55.6–66.7) | 55.6% |

Hard-18 accuracy, run by run:

| | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|
| Jev `jev-latest` | 72.2 | 72.2 | 72.2 | 77.8 | 72.2 |
| Jev `jev-1.13.0` | 77.8 | 77.8 | 72.2 | 72.2 | 77.8 |
| GPT-5.4 | 66.7 | 72.2 | 66.7 | 72.2 | 72.2 |
| Sonnet 5 | 66.7 | 66.7 | 66.7 | 72.2 | 61.1 |
| Gemini 3.1 Pro | 66.7 | 61.1 | 66.7 | 55.6 | 66.7 |

**The headline, by the pre-registered rule: shrinks.** Jev's mean on the hard 18 is above every
frontier model's mean, but its run range overlaps GPT-5.4's and Sonnet 5's: Jev's worst run, 72.2%, equals the best run of
GPT-5.4 and of Sonnet 5. Gemini 3.1 Pro never got above 66.7%. (Corrected 2026-09-23 from "equals
the best run of all three"; see the correction under the answer to Test 4.) Lead on means: +3.3 points over GPT-5.4, +6.7 over Sonnet 5, +10.0 over Gemini 3.1 Pro.
One claim is 5.6 points, so the lead over the best of them is 0.6 of one claim.

**The part that did not move.** The structural finding of the first article holds on every run:
the three frontier models scored 100% on the easy 24 in all fifteen of their runs, and Jev scored
91.7% in all ten of its runs, missing `ctl-03` and `ctl-17` every time. Whatever advantage Jev has
is on the hard 18 and nowhere else. The easy set's scores never varied.

**Where the variation lives.** Of the 18 hard claims, Jev answers 16 identically on every run. The
spread comes from two: `sb-06` (right 3 of 5) and `sb-07` (3 of 5). GPT-5.4 wavers on one, `rz-03`
(3 of 5). Sonnet 5 on two, `sb-06` (4 of 5) and `sb-07` (1 of 5). Gemini 3.1 Pro on three, `rz-05`
(1 of 5), `rz-06` (4 of 5) and `rz-07` (2 of 5). The full 42-by-5 table of how many runs got each
claim right is in the analysis file.

Five hard claims are missed by every system on every run: `sb-03`, `rb-04`, and, for everything
except GPT-5.4, `rz-03` and `rz-04`. `sb-03` and `rb-04` are 0 of 25 across all five systems.

## Against the numbers: Test 4

Exact McNemar on majority-of-five correctness, hard 18, Jev `jev-latest` against each:

- GPT-5.4: Jev alone right on 3 (`rz-05`, `rz-06`, `sb-06`), GPT-5.4 alone right on 2 (`rz-03`,
  `rz-04`). **p = 1.000.** Run-by-run p = 1.000 on all five pairs.
- Sonnet 5: 2 and 0 (`rz-07`, `sb-07`). **p = 0.500.** Run by run 0.500 to 1.000.
- Gemini 3.1 Pro: 3 and 0 (`rz-05`, `sb-06`, `rz-07`). **p = 0.250.** Run by run 0.125 to 1.000.

**So "Jev beats the frontier models on the hard set" is not a supportable sentence on this
evidence.** What is supportable: across five runs Jev's mean on the hard 18 is the highest of the
four, by 3.3 to 10.0 points, at about a fiftieth to a two-hundredth of the cost per claim, and the
frontier models beat it on the easy 24 every time.

## Jev determinism, identical input five times

| Jev arm | label differs | confidence differs | distribution differs | largest confidence gap |
|---|---|---|---|---|
| `jev-latest`, schema | 2 of 42 | 28 | 28 | 0.29 (`rz-03`) |
| `jev-1.13.0`, schema | 2 of 42 | 29 | 25 | 0.22 (`ctl-10`) |
| split | 1 of 42 | 32 | 29 | 0.16 |
| fan-out | 2 of 42 | 39 | 40 | 0.18 |

"Confidence differs" and "distribution differs" are separate counts: a confidence can change while
the reported probabilities, rounded to two places, do not, and the other way round.

The single largest movement in any one label's probability across the five `jev-latest` runs is
0.20.

**Every Choice label flip happened at low confidence.** `sb-06` ran 0.25 to 0.46 and `sb-07` 0.17
to 0.25 on `jev-latest`, the same two rows at 0.26 to 0.41 and 0.17 to 0.29 on `jev-1.13.0`, and
`ctl-03` at 0.29 to 0.36 in the split arm. In the fan-out arm the two flips, `ctl-01` and
`ctl-10`, are rows where the `faithful` answer sits on the 0.5 threshold, 0.39 to 0.53.

**Is caching a Jev verdict safe?** Not for identical input in general: the label can change and
the confidence usually does. On this evidence it is safe above 0.5 confidence: no claim that
reached 0.5 on any run changed label, in any of the 420 schema-only calls across both model names. That matches the escalation
threshold the first verdict already recommended. TypeSafe's documentation does not promise
determinism, and its own self-consistency cookbook reports run-to-run movement in Jev's
probabilities.

## Test 3 — three arms, each against its own baseline

| arm | all 42, mean (range) | hard 18 | baseline, all 42 | McNemar, all 42 | pre-registered reading |
|---|---|---|---|---|---|
| (a) Jev pinned `jev-1.13.0` | 84.8% (83.3–85.7) | 75.6% | 83.8% (83.3–85.7) | 0 and 0, p = 1.000 | no detectable effect |
| (b) Jev split | 82.4% (81.0–83.3) | 72.2% | 83.8% (83.3–85.7) | 3 and 2, p = 1.000 | moved beyond noise, not significant |
| (b) GPT-5.4 split, one run | 88.1% | 72.2% | 87.1% (85.7–88.1) | 2 and 2, p = 1.000 | no detectable effect |
| (b) Sonnet 5 split, one run | 85.7% | 66.7% | 85.7% (83.3–88.1) | 2 and 2, p = 1.000 | no detectable effect |
| (b) Gemini 3.1 Pro split, one run | 83.3% | 61.1% | 84.3% (81.0–85.7) | 2 and 2, p = 1.000 | no detectable effect |
| (c) Jev fan-out | 77.6% (76.2–81.0) | 66.7% | 83.8% (83.3–85.7) | 5 and 1, p = 0.219 | moved beyond noise, not significant |

McNemar is on majority-of-five correctness, baseline-only-right then arm-only-right. For the three
one-run LLM split arms it is that run against the model's own five schema-only runs. The three
"2 and 2" results are three different sets of rows (listed below), checked by hand.

### (a) Pin the version

**The alias has not moved in a way anyone could detect.** Every `jev-latest` call today reports
`jev-1.13.0` as the model that answered, which is what TypeSafe's models page says the alias points
to. Majority-of-five correctness is identical between the two names on all 42 claims. The distributions
are not identical run for run, but they are not identical run for run within one name either.
Today's first `jev-latest` run differs from the 20 September file on one label, `sb-06`, which is
one of the two rows that flips between today's own runs.

What this cannot prove: the 20 September run did not record the served model, so it cannot be shown
that it was `jev-1.13.0`. Nothing in the answers suggests otherwise.

Pinning is still right in production: the alias will move when a new release ships. It just
explains none of the result here.

### (b) Split the compound label

**For Jev it made things slightly worse, and moved the errors around.** Gained: `rb-04` (0 of 5 to
5 of 5), `sb-07` (3 to 5), `ctl-03` (0 to 3). Lost: `rb-02` (5 to 0, now called `not_addressed`),
`ctl-01` (5 to 0, now `altered`), `sb-06` (3 to 0, now `altered`). Net, 1.4 points lower on all 42
and 1.1 points lower on the hard 18, with a range of zero on the hard 18: 72.2% on all five runs.

**For the frontier models it traded two rows for two rows, each.**

- GPT-5.4 fixed `rz-05` and `rz-06`, both right 0 of 5 schema-only, and lost `rz-03` and `rz-07`.
- Sonnet 5 fixed `sb-03`, the spliced quotation that nothing else caught, and `sb-07`, and lost
  `sb-06` and `rb-02`.
- Gemini 3.1 Pro fixed `sb-03` and `rz-07`, and lost `sb-07` and `rz-06`.

**The four rows Test 2 named**, where the frontier models' reasoning talked `supported` claims down
to `unsupported`. Schema-only times right out of five, then the split arm's answer:

| | Jev | GPT-5.4 | Sonnet 5 | Gemini 3.1 Pro |
|---|---|---|---|---|
| `rz-05` | 5/5, supported | 0/5, **supported** | 5/5, supported | 1/5, not_addressed |
| `rz-06` | 5/5, supported | 0/5, **supported** | 5/5, supported | 4/5, altered |
| `sb-04` | 5/5, supported | 5/5, supported | 5/5, supported | 5/5, supported |
| `sb-06` | 3/5, altered ×5 | 0/5, altered | 4/5, altered | 0/5, altered |

The split fixed GPT-5.4 on exactly the two rows the last sentence of the `altered` definition was
written from, and that sentence was written knowing Test 2's results. That was declared in the
pre-registration and it is the reason the gain on those two rows should be read as the definition
doing what it was written to do, not as independent evidence. Every system called `sb-06` `altered`,
on every run. The claim says the paper leaves the attribution "unattributed"; the paper does not use
that word. The dataset labels it `supported` as a fair paraphrase. With a named category for
"changed the wording", all four systems disagree with that label.

How the four-way answers fell, Jev, all five runs pooled: of the 95 answers on true-`unsupported`
rows, 55 `contradicted`, 15 `altered`, 20 `supported`, 5 `not_addressed`. Jev reaches for
`contradicted` far more often than for `altered`, although most of the dataset's `unsupported`
rows are described in their `why` records as alterations rather than contradictions. The frontier
models split their `unsupported` answers
10 or 12 `contradicted` to 5 to 7 `altered`. Full tallies are in the analysis file.

### (c) Multi-question fan-out

**Same cost, lower score.** Three Nouls in one call cost $0.000026 per claim against $0.000025 for
the single Choice, 1.04 times, on 610 input tokens against 587, at the same 0.22 seconds. The
billing claim holds: extra questions over the same state are close to free.

The accuracy fell. 77.6% on all 42 against 83.8%, and 66.7% on the hard 18 on every run, against
73.3%. Gained `rz-04` (0 to 5 of 5), the non-reversal the single Choice misses every time. Lost
`sb-06`, `sb-07`, `rz-05` (all to 0 of 5), `ctl-01` (5 to 2) and `ctl-10` (5 to 1).

The losses have one shape. On `rz-05`, `sb-06`, `ctl-01` and `ctl-10`, all labelled `supported`,
the `faithful` question comes back between 0.14 and 0.53: Jev is reluctant to say "everything the
claim states is in the passage" about a paraphrase, and the pre-registered rule sends any
`faithful` below 0.5 to `unsupported`. `sb-07`, a claim about the author's own literature search,
scores 0.70 to 0.74 on `addresses`, so the rule never reaches `not_addressed`. The single Choice judges the relation as a whole and does better on
exactly those rows.

This is one decomposition and one combination rule, fixed before the run. A different rule, or a
threshold tuned on these results, would score differently, and tuning it on these 42 claims would
make the score meaningless. What this arm shows is that the vendor's recommended shape is not
automatically better for this job, not that fan-out cannot work.

## What it cost

| | measured spend |
|---|---|
| Jev, 20 runs, all four arms | $0.0218 |
| GPT-5.4, 6 runs | $0.3356 |
| Sonnet 5, 6 runs | $0.5862 |
| Gemini 3.1 Pro, 6 runs | $1.3073 |
| **Total** | **$2.2510** against a $10 cap and a $2.90 projection |

Per claim, schema-only, today: Jev $0.000025, GPT-5.4 $0.001289, Sonnet 5 $0.002259, Gemini 3.1 Pro
$0.004940. The frontier figures are OpenRouter's reported charges, summed from `charged_usd`; Jev's
is its reported input tokens at $0.042 per million.

## Honest limits

1. **n = 18 on the set that carries the headline, and five runs.** Five runs is enough to show that
   the spread exists and where it lives. It is not enough to pin a mean to better than a claim, and
   no comparison in this file is significant.
2. **Majority-of-five McNemar throws information away.** A claim right 3 of 5 counts as fully right.
   It was chosen in advance because it keeps the test exact and re-derivable by hand. A test that
   used all five runs per claim would be more powerful and was not pre-registered.
3. **The LLM split arms are one run each**, against five. Their "no detectable effect" readings are
   one draw against a spread.
4. **Arm (a) compared a model with itself.** `jev-latest` and `jev-1.13.0` resolve to the same
   version today. It answered the alias question and doubled the Jev sample; it did not test
   pinning against a moved alias, which cannot be tested until the alias moves.
5. **The `altered` definition's last sentence was written knowing Test 2's results**, from the
   `why` records of `rz-05`, `rz-06` and `sb-04`. Declared before the run. GPT-5.4's gain on
   `rz-05` and `rz-06` is exactly that sentence working, not an independent finding.
6. **Arm (b) changes the definitions, not only the number of options.** The two new definitions
   are more specific than the baseline's `unsupported` text. A split with vaguer definitions, or a
   more specific three-way definition with no split, would separate those two effects. Neither was
   run.
7. **The fan-out result is one decomposition and one rule.** See (c).
8. **Temperature and seed stay unset on both sides**, as in every earlier run, because the point
   was to measure the setup the first article measured. A frontier model at temperature 0 would
   likely vary less. The five runs of each system ran side by side in one 19-minute window, not
   across days, so drift across days is not measured.
9. **The labels are still single-annotator.** `sb-06` is labelled `supported`, and every system
   called it `altered` on every split run. Weakness 7 in the README stands.
10. **Test 2 was not repeated.** Its reasoning-allowed arms are one run each. Test 2's 16.7-point
    lead was measured from Jev's 77.8% single run, which today's evidence puts at the top of Jev's
    range. Against Jev's typical 72.2% it would be 11.1 points, still one draw on the frontier side.
11. **The README's result table labels Jev's 20 September row `jev-1.13.0`.** The file it comes
    from called `jev-latest`, and the served version was not recorded. Today's evidence says it was
    very probably the same model; the label claims more than the file shows.

## What this changes

README weakness 6 has an answer, and it is not the flattering one: an 11-point gap on 18 claims was
mostly one good run. Across five runs the lead is 3.3 points over the best frontier model and is
not significant against any of them.

Weaknesses 3, 4 and 5 have answers too: pinning, splitting the label and fanning out explained none
of Jev's result. On this set, Jev asked the obvious way was Jev at its best.

What survives from the first article is the shape rather than the size: the frontier models are
perfect on the constructed controls and Jev is not, every run. On the real published sentences Jev
is at least level with them, at about a fiftieth to a two-hundredth of the cost. It is not a
reliable winner, and a verdict it gives below 0.5 confidence can change if you ask again.
