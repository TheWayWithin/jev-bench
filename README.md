# jev-bench

**Does the source actually say it?** A 42-claim benchmark for one narrow job: given a sentence that
makes a claim and the passage it cites, decide whether the passage supports the sentence as written.

Run on 20 September 2026 against **Jev** (TypeSafe's System One model, which returns a typed answer
and a probability instead of text) and three frontier models. Everything here is the real thing: the
claims, the code, the raw per-claim output, and the scored results.

Write-up: **[Jev is not an LLM](https://jamiewatters.work/journey/jev-is-not-an-llm)**

☕ **[Buy me a coffee](https://buymeacoffee.com/jamiewatters)** if this saved you an afternoon.

---

## The result

| | all 42 | the easy 24 | the hard 18 | cost per claim | seconds |
|---|---|---|---|---|---|
| **Jev** `jev-1.13.0` | 85.7% | 91.7% | **77.8%** | **$0.000025** | **0.23** |
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

**On calibration.** GPT-5.4 and Gemini put all 42 answers in their top confidence bucket. Sonnet 5
put 39 of 42 there. All three were right about 85% of the time, so their stated confidence cannot
tell you which answers to check. Jev used four buckets: its top bucket (0.8 and above, 29 items) was
right 93.1% of the time and everything below was right 60 to 80%.

**On risk and coverage** (added 21 September, from the same runs, no new model calls). Auto-accept
every verdict at or above a confidence threshold and escalate the rest. On all 42 claims Jev's
threshold actually does something: at 0.95 it keeps 57.1% of claims and is wrong on 4.2% of them, at 0.80
it keeps 69.0% and is wrong on 6.9%. Changing GPT-5.4's threshold does nothing at all: 100% coverage and 14.3%
error at every setting from 0.60 to 0.90, and Gemini's behaves the same way. Sonnet 5's does move.

**On the hard 18, no model's threshold reaches an error rate you would accept.** Jev's best is
14.3% error at 38.9% coverage; nothing in the grid gets under 10%. Run `risk_coverage.py` for the
full grid, the gate view, and the cascade.

## What is in here

```
dataset/claims.jsonl   the 42 labelled claims, one JSON object per line
run.py                 runs one or both systems, writes results/<system>-<model>-<timestamp>.jsonl
score.py               accuracy, per class, reliability table, cost, latency, and the decision rule
risk_coverage.py       coverage and error rate at each confidence threshold, plus the cascade
prices.json            published prices, each with the page it was read from
results/               every run from 20 September, plus the scored output and the verdict
bench.sh               wrapper so you do not have to remember the venv path
```

`results/2026-09-20-verdict.md` is the short version: numbers, the rule, and the honest limits.

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

- `supported` — the passage states the claim, or directly implies it.
- `unsupported` — the passage addresses this and does not support the claim as written. Covers flat
  contradiction and, more often, a claim that is right in substance but wrong in version, figure,
  attribution, scope or wording.
- `not_addressed` — the passage does not speak to the claim either way.

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

A full four-model run is 42 claims each and costs about 35 cents.

## Known weaknesses

Named here rather than left for you to find.

1. **The frontier models answered into a JSON schema with no room to reason first.** That is not how
   anyone sensible uses them on this task, and Jev pays no equivalent cost because it was never
   going to reason out loud. The hard-set gap is a gap against schema-constrained models until a
   rerun says otherwise. **This is the next experiment.**
2. **The two confidence numbers may not be the same kind of object.** Jev's is a probability the
   model is built to return. The frontier figure is a number requested in a JSON field, which is
   self-report. That is the right comparison for a pipeline, because self-report is what you would
   actually receive, and it is not a like-for-like calibration test.
3. **The runs called `jev-latest`, a moving alias, rather than pinning `jev-1.13.0`.** Aliases move
   silently. Pin the version.
4. **`unsupported` is a compound label.** TypeSafe's own guidance is that Jev answers the question
   you wrote rather than the one you meant, so handing a literal model a two-things-in-one category
   may cost it accuracy.
5. **One Choice question**, where the product sells multiple questions fanned out over the same
   state in one pass, billed once on input. The recommended shape was never tested.
6. **One run per model, no repeats.** No error bars. An eleven-point gap on 18 items is two claims.
7. **The labels are not independent of the author.** The sentences, the sources they cite and the
   audits that judge them all come from one person's publishing pipeline. Hand-checking against the
   primaries reduces that; it does not remove it.
8. **Gemini 3.1 Pro is a preview build**, and all frontier latency is measured end to end through
   OpenRouter, including its routing hop.

## Contributing

Two things are genuinely useful.

**More Tier A claims**, from your own corrections: a real published sentence, the passage it cites,
the label, and one line on why. Independent claims from somebody else's pipeline would fix weakness
7 outright, and that is the weakness I cannot fix myself.

**A rerun of anything here.** Different models, a pinned version, repeats, or the reasoning-allowed
baseline in weakness 1. Open an issue with the results file attached.

## Licence

MIT for the code. The claims quote short passages from three arXiv papers (SkillsBench
[2602.12670](https://arxiv.org/abs/2602.12670), ReasoningBank
[2509.25140](https://arxiv.org/abs/2509.25140), R-Zero
[2508.05004](https://arxiv.org/abs/2508.05004)) for the purpose of criticism and review; each row
names its source and section.

---

Built by [Jamie Watters](https://jamiewatters.work). If it was useful,
[buy me a coffee](https://buymeacoffee.com/jamiewatters).
