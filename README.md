# jev-bench

**Does the source actually say it?** A 42-claim benchmark for one narrow job: given a sentence that
makes a claim and the passage it cites, decide whether the passage supports the sentence as written.

## Current result

Five runs per model, 22 September 2026. On the hard 18, **Jev ties GPT-5.4**: 73.3% mean against
70.0%, a 3.3-point lead that is 0.6 of one claim and not significant (exact McNemar p = 1.000). It
gets there at about a fiftieth of GPT-5.4's cost per claim. On the easy 24 the frontier models score
100% in every run and Jev 91.7%. Full numbers, the three question-design arms and the honest limits
are in `results/2026-09-23-tests-3-4-verdict.md`.

Run on 20 September 2026 against **Jev** (TypeSafe's System One model, which returns a typed answer
and a probability instead of text) and three frontier models, again on 21 September with the
frontier models allowed to reason first, and five times each on 22 September. Everything here is the real thing: the claims, the code,
the raw per-claim output, and the scored results.

Write-up: **[Jev ties GPT-5.4](https://jamiewatters.work/journey/jev-ties-gpt-5-4)**. Earlier:
[Jev is not an LLM](https://jamiewatters.work/journey/jev-is-not-an-llm) and
[the confidence-threshold follow-up](https://jamiewatters.work/journey/confidence-threshold-fact-checking).

☕ **[Buy me a coffee](https://buymeacoffee.com/jamiewatters)** if this saved you an afternoon.

---

## First run, 20 September (single run, superseded)

| | all 42 | the easy 24 | the hard 18 | cost per claim | seconds |
|---|---|---|---|---|---|
| **Jev** `jev-latest` | 85.7% | 91.7% | **77.8%** | **$0.000025** | **0.23** |
| GPT-5.4 | 85.7% | 100% | 66.7% | $0.001289 | 1.01 |
| Claude Sonnet 5 | 85.7% | 100% | 66.7% | $0.002228 | 2.76 |
| Gemini 3.1 Pro | 81.0% | 100% | 55.6% | $0.004824 | 3.78 |

The frontier models are perfect on constructed controls and fall over on real published sentences.
Jev is the reverse. That inversion, not the headline accuracy, is what the benchmark is for.

**Three models scoring 85.7% is a coincidence of totals, not a duplicated file.** That is 36 of 42
three times over, reached by different routes. Jev's misses are `ctl-03`, `ctl-17`, `rb-04`,
`rz-03`, `rz-04`, `sb-03`; GPT-5.4's are `rb-04`, `rz-03`, `rz-05`, `rz-06`, `sb-03`, `sb-06`;
Sonnet 5's are `rb-04`, `rz-03`, `rz-04`, `rz-07`, `sb-03`, `sb-07`. No two models produced
identical answers: the closest pair agreed on 40 of 42 and the rest on 36 to 38. Check it yourself
against the JSONL files in `results/`. Note the structural difference the tie hides: two of Jev's
six errors are in the easy set, while every error the three frontier models made is in the hard 18.

**On calibration.** GPT-5.4 and Gemini put all 42 answers in their top confidence bucket (0.8 and
above). Sonnet 5 put 39 of 42 there. GPT-5.4 and Sonnet 5 were right 85.7% of the time and Gemini
81.0%, all well short of the 0.8-plus confidence they stated, which makes them badly calibrated:
the number they state runs well ahead of the accuracy they deliver. That is not
the same as the number carrying no information at all, which an earlier version of this section
claimed. See risk and coverage below, corrected the same day. Jev used four buckets: its top
bucket (0.8 and above, 29 items) was right 93.1% of the time and everything below was right 60 to
80%.

**On risk and coverage** (added 21 September, from the same runs, no new model calls; corrected
21 September, hours later: the first version tested six round thresholds, 0.60 to 0.95, and
GPT-5.4's 42 answers all sit between 0.94 and 0.99, so five of those six thresholds sat off its
range and told us nothing). Auto-accept every verdict at or above a confidence threshold and
escalate the rest. Swept over each model's own distinct values instead of a fixed grid: Jev runs
from 28.6% coverage at 0.0% error up to 100% at 14.3%. GPT-5.4 runs from 64.3% coverage at 3.7%
error up to 100% at 14.3%, and beats Jev at every coverage level the two share but the top, where
both accept everything and land on the same 14.3% error. Gemini has three
distinct values and one useful cut: 76.2% coverage at 9.4% error, rising to 100% at 19.0%. Sonnet
5's moves too. None of the four was flat; the six-point grid just missed GPT-5.4's and Gemini's
actual range. Full derivation: [the follow-up
piece](https://jamiewatters.work/journey/confidence-threshold-fact-checking).

**On the hard 18, no model's threshold reaches an error rate you would accept.** Jev's best inside
the original six-point grid is 14.3% error at 38.9% coverage; nothing in that grid gets under 10%.
Swept over each model's own values instead, two of the four touch 0% error, but only by accepting
one to three of the 18 claims, not a coverage level worth having. Run `risk_coverage.py --sweep-own`
for the full grid, the gate view, and the cascade.

## And when the frontier models are allowed to think first

Added 21 September. Every reviewer of the first write-up raised the same objection: those three
models were forced straight into a JSON verdict with no room to reason, so the hard-set gap was a
result about schema-constrained models rather than about the models. So it was re-run with a
free-text scratchpad in front of the same structured verdict.

| on the hard 18 | schema only | reasoning allowed | cost per claim | seconds |
|---|---|---|---|---|
| GPT-5.4 | 66.7% | 61.1% | $0.001289 → $0.005450 | 1.01 → 3.77 |
| Claude Sonnet 5 | 66.7% | 44.4% | $0.002228 → $0.006439 | 2.76 → 6.23 |
| Gemini 3.1 Pro | 55.6% | 55.6% | $0.004824 → $0.011545 | 3.78 → 8.71 |

**The gap did not close.** None of the three improved, Gemini answered all 18 identically, and Jev's
lead over the best of them goes from 11.1 points to 16.7. The reasoning arm cost 2.4 to 4.2 times as
much per claim.

**Read those two leads with the five-run result in mind.** Both are measured from Jev's single
20 September run, 77.8% on the hard 18. Five repeats on 22 September put that at the top of Jev's
range: four of the five scored 72.2%. Against 72.2%, the lead over the best reasoning-allowed model
is 11.1 points, not 16.7. The reasoning-allowed arms themselves were run once each and have not been
repeated.

**What this does not say.** No per-model drop is significant on 18 items: exact McNemar gives
p = 1.000, 0.219 and 1.000. "Reasoning did not help" is supportable. "Reasoning made them worse" is
not. Run `python3 mcnemar.py` to check that yourself. The full side-by-side and eleven limits,
including that for two of the three models the verdict call only transcribes the scratchpad rather
than re-deciding it, are in `results/2026-09-22-test2-verdict.md`.

## What is in here

```
dataset/claims.jsonl   the 42 labelled claims, one JSON object per line
run.py                 runs one or both systems, writes results/<system>-<model>-<timestamp>.jsonl
score.py               accuracy, per class, reliability table, cost, latency, and the decision rule
risk_coverage.py       coverage and error rate at each confidence threshold, plus the cascade
mcnemar.py             exact McNemar on the hard 18: is a gap between two runs bigger than luck
tests34.py             Tests 3 and 4: the run plan, the spend check, and every number in the verdict
test2_checks.py        the per-row and per-model checks behind the Test 2 write-up
prices.json            published prices, each with the page it was read from
results/               every run, 20, 21 and 22 September, plus the scored output and the verdicts
bench.sh               wrapper so you do not have to remember the venv path
```

`results/2026-09-20-verdict.md` is the rule and the honest limits, written up from an earlier,
separate two-model run against `anthropic/claude-sonnet-4.5` rather than the four-model comparison
in the table above. Its headline numbers (76.2% baseline accuracy) do not match that table's, on
purpose, because it is a different run. It was superseded by the four-model first run, which was in
turn superseded by the five-run result at the top of this README; kept for the record, and cross-checked against its own data in this correction.

## The labelled set

Two tiers, scored separately, because they are not the same kind of evidence.

**Tier A, 18 claims, real and adversarial.** Verbatim sentences from a published article, paired
with the source passage they cite, labelled from nine independent source audits of the underlying
papers. These are sentences that survived writing, an automated gate and a first round of review,
and were still wrong. The commonest fault is not a flat contradiction: it is a true number pointed
at the wrong quantity, or a genuine quote assembled from two places in a paper.

**Tier B, 24 claims, constructed controls.** Built from passages quoted verbatim in those audits. A
sentence that restates the passage. The same sentence with one digit changed. A claim about
something the passage does not mention. These exist so the calibration curve has enough points to
mean anything. They are easier by construction.

Headline numbers come from Tier A. Tier B is reported alongside and never merged into it.

### Labels

- `supported`: the passage states the claim, or directly implies it.
- `unsupported`: the passage addresses this and does not support the claim as written. Covers flat
  contradiction and, more often, a claim that is right in substance but wrong in version, figure,
  attribution, scope or wording.
- `not_addressed`: the passage does not speak to the claim either way.

`unsupported` deliberately merges contradiction with correct-but-altered, because for a publishing
gate those are the same event: do not publish this sentence. That is a design choice with a cost,
and it is listed under Known weaknesses below.

Each row also carries `tier`, `source`, `provenance` (whether the passage is quoted verbatim in the
audit or assembled from what the audit reports) and `why` (one line on the label). One Tier A row is
marked `contested`, because a careful person could argue it either way.

## The decision rule, written before the first run

Recorded so the write-up could not become a story about whichever way it landed.

Jev replaces the check in an automated publishing gate only if **recall on `unsupported` is at least
0.80** and at least as good as the frontier models', **precision on `unsupported` is at least 0.60**,
and it is cheaper and faster. Below 0.60 recall it is a no. Between the two it is a pre-filter that
escalates what it is unsure about.

**It landed in the middle.** 78.9% recall against the 80% bar, one item short, with 88.2% precision
against GPT-5.4's 81.0%. So: pre-filter, not replacement.

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install typesafe-sdk openai
cp .env.example .env     # then paste your keys in
bash bench.sh --system jev --tier A      # 18 claims, the hard half
bash bench.sh --system both              # all 42, both systems

# the reasoning-allowed arm: a free-text scratchpad, then the same JSON verdict
python3 run.py --system llm --arm reasoning --llm-model openai/gpt-5.4
.venv/bin/python score.py results/jev-<ts>.jsonl results/llm-<model>-<ts>.jsonl

# how much checking you could stop doing: coverage and error rate per threshold
python3 risk_coverage.py results/*.jsonl
python3 risk_coverage.py --cascade results/jev-<ts>.jsonl results/llm-<model>-<ts>.jsonl
```

`risk_coverage.py` needs no keys and no venv: it reads the JSONL files that are already here.

You need a `TYPESAFE_API_KEY` from [console.typesafe.ai](https://console.typesafe.ai/) and an
`OPENROUTER_API_KEY` from [openrouter.ai](https://openrouter.ai/keys). Pick baselines with
`--llm-model`, using any OpenRouter slug: `openai/gpt-5.4`, `anthropic/claude-sonnet-5`,
`google/gemini-3.1-pro-preview`.

A full four-model run is 42 claims each and costs about 35 cents. The reasoning-allowed arm across
the three frontier models is 42 claims each again, two calls per claim, and cost $0.98: sum
`charged_usd` over the three 21 September files and you get $0.9842.

## Known weaknesses

Named here rather than left for you to find.

1. **~~The frontier models answered into a JSON schema with no room to reason first.~~ Answered
   21 September, and the answer is no: the gap is not an artefact of the schema.** Given a
   scratchpad first, none of the three improved on the hard 18 and two scored lower, at 2.4 to 4.2
   times the cost per claim. See the table above and
   `results/2026-09-22-test2-verdict.md`. What replaces it as the live weakness is **limit 3 of
   that run**: for GPT-5.4 and Sonnet 5 the verdict call emits 21 to 25 tokens, so it transcribes
   the scratchpad rather than re-deciding on it. This arm measures "think, then transcribe". A
   single relaxed-schema call, or a verdict step made to re-argue, would measure something else.
2. **The two confidence numbers may not be the same kind of object.** Jev's is a probability the
   model is built to return. The frontier figure is a number requested in a JSON field, which is
   self-report. That is the right comparison for a pipeline, because self-report is what you would
   actually receive, and it is not a like-for-like calibration test.
3. **~~The runs called `jev-latest`, a moving alias, rather than pinning `jev-1.13.0`.~~ Answered
   22 September: it made no difference.** Every `jev-latest` call now reports `jev-1.13.0` as the
   model that answered, and five runs on each name are right or wrong by majority on exactly the same claims, all 42. The
   20 September run did not record the served version, so that one cannot be proved; nothing in its
   answers suggests the alias has moved. Pin anyway in production. See
   `results/2026-09-23-tests-3-4-verdict.md`, Test 3(a).
4. **~~`unsupported` is a compound label.~~ Answered 22 September: splitting it did not help.**
   Offered `contradicted` and `altered` separately, scored back as `unsupported`, Jev dropped 1.4
   points on all 42 and none of the three frontier models moved outside its own run-to-run spread.
   It did show that every system calls `sb-06` altered, which says more about that label than
   about the models. Test 3(b) in the same verdict.
5. **~~One Choice question~~ Answered 22 September: the recommended fan-out cost the same and
   scored lower.** Three Noul questions in one call, combined by a rule fixed in advance, cost 1.04
   times the single Choice and scored 77.6% against 83.8% on all 42 (p = 0.219, not significant).
   One decomposition and one rule, so this says the recommended shape is not automatically better
   for this job, not that it cannot work. Test 3(c).
6. **~~One run per model, no repeats.~~ Answered 22 September, and the answer cuts against the first
   write-up.** Five runs each: Jev's lead on the hard 18 over the best frontier model is 3.3 points
   on means, not 11.1, and is not significant against any of the three. The 20 September Jev run
   was its best result, which it matched in one of five runs today. The easy-set pattern held on
   every run. Jev is also not deterministic: across identical calls the label changed on 2 of 42
   claims, always below 0.47 confidence. Run `python3 tests34.py analyse` to re-derive it with no
   keys. The Test 2 reasoning-allowed arms are still one run each.
7. **The labels are not independent of the author.** The sentences, the sources they cite and the
   audits that judge them all come from one person's publishing pipeline. Hand-checking against the
   primaries reduces that; it does not remove it.
8. **Gemini 3.1 Pro is a preview build**, and all frontier latency is measured end to end through
   OpenRouter, including its routing hop.
9. **`score.py`'s reliability table uses five buckets of 0.2 each**, a standard convention for
   expected calibration error and left unchanged here. It is the wrong tool for judging whether a
   model's confidence discriminates its own right answers from wrong ones within a bucket, which
   is what hid GPT-5.4's real range on 21 September: its whole 0.94-to-0.99 spread sits inside one
   0.8-to-1.0 bucket. Use `risk_coverage.py --sweep-own` for that question, not the bucket table.

## Contributing

Two things are genuinely useful.

**More Tier A claims**, from your own corrections: a real published sentence, the passage it cites,
the label, and one line on why. Independent claims from somebody else's pipeline would fix weakness
7 outright, and that is the weakness I cannot fix myself.

**A rerun of anything here.** Different models, or repeats on different days: repeats most of all.
The 22 September repeats cut an 11.1-point gap to 3.3, but they ran in one 19-minute window, and the
21 September reasoning-allowed arm has still been run only once per model. Open an issue with the results file attached.

## Licence

MIT for the code. The claims quote short passages from three arXiv papers (SkillsBench
[2602.12670](https://arxiv.org/abs/2602.12670), ReasoningBank
[2509.25140](https://arxiv.org/abs/2509.25140), R-Zero
[2508.05004](https://arxiv.org/abs/2508.05004)) for the purpose of criticism and review; each row
names its source and section.

---

Built by [Jamie Watters](https://jamiewatters.work). If it was useful,
[buy me a coffee](https://buymeacoffee.com/jamiewatters).
