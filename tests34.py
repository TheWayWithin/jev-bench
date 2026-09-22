#!/usr/bin/env python3
"""Tests 3 and 4: the run plan, the spend check, and the analysis.

    python3 tests34.py plan       print every run and the projected spend; needs no keys
    python3 tests34.py run        re-check the projection, stop if over the cap, then run
    python3 tests34.py analyse    every number in the verdict, from the JSONL in results/;
                                  needs no keys

The design, the arms, the combination rule and the decision rules are fixed in
results/2026-09-22-tests-3-4-preregistration.md, committed before any run.
"""

import glob
import json
import pathlib
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from mcnemar import exact_two_sided

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
PY = sys.executable
REPEATS = 5
CAP_USD = 10.00

LLMS = ["openai/gpt-5.4", "anthropic/claude-sonnet-5", "google/gemini-3.1-pro-preview"]
LLM_NAMES = {"openai/gpt-5.4": "GPT-5.4", "anthropic/claude-sonnet-5": "Sonnet 5",
             "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro"}

# The schema-only runs of 20 September, the per-claim costs the projection is built from.
BASE_FILES = {
    "jev": "results/jev-20260920-114958.jsonl",
    "openai/gpt-5.4": "results/llm-openai-gpt-5.4-20260920-142048.jsonl",
    "anthropic/claude-sonnet-5": "results/llm-anthropic-claude-sonnet-5-20260920-141849.jsonl",
    "google/gemini-3.1-pro-preview":
        "results/llm-google-gemini-3.1-pro-preview-20260920-142133.jsonl",
}
JEV_PER_MTOK = 0.042

# Headroom on the projection. The split prompt is longer than the baseline's; the fan-out
# sends three questions instead of one. Both multipliers are deliberately generous.
SPLIT_MULT = 1.5
FANOUT_MULT = 4.0
SAFETY = 1.25

# The four rows Test 2 found the frontier models' new errors on, reported by name.
BOUNDARY_ROWS = ["rz-05", "rz-06", "sb-04", "sb-06"]


def slug(model):
    return model.replace("/", "-").replace(":", "-")


def plan():
    """Every run, as (system, model, arm, label). One label per output file."""
    runs = []
    for i in range(1, REPEATS + 1):
        runs.append(("jev", "jev-latest", "schema", f"t4-r{i}"))          # Test 4
        runs.append(("jev", "jev-1.13.0", "schema", f"t4pin-r{i}"))       # Test 4 and 3(a)
        runs.append(("jev", "jev-latest", "split", f"t3b-r{i}"))          # Test 3(b)
        runs.append(("jev", "jev-latest", "fanout", f"t3c-r{i}"))         # Test 3(c)
        for m in LLMS:
            runs.append(("llm", m, "schema", f"t4-r{i}"))                 # Test 4
    for m in LLMS:
        runs.append(("llm", m, "split", "t3b-r1"))                        # Test 3(b), once
    return runs


def load(path):
    with open(HERE / path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def per_claim_cost():
    """Measured cost per claim of one schema-only call, per system, from 20 September."""
    out = {}
    for key, path in BASE_FILES.items():
        rows = load(path)
        if key == "jev":
            out[key] = sum(r["input_tokens"] for r in rows) / len(rows) / 1e6 * JEV_PER_MTOK
        else:
            out[key] = sum(r["charged_usd"] for r in rows) / len(rows)
    return out


def projection(runs, n_claims=42):
    cpc = per_claim_cost()
    lines, total = [], 0.0
    for system, model, arm, label in runs:
        base = cpc["jev"] if system == "jev" else cpc[model]
        mult = {"split": SPLIT_MULT, "fanout": FANOUT_MULT}.get(arm, 1.0)
        cost = base * mult * n_claims
        total += cost
        lines.append((system, model, arm, label, cost))
    return lines, total * SAFETY


def cmd_plan():
    runs = plan()
    lines, projected = projection(runs)
    cpc = per_claim_cost()
    print("Measured cost per claim, schema-only, 20 September files:")
    for k, v in cpc.items():
        print(f"  {k:<32} ${v:.6f}")
    print(f"\n{len(runs)} runs of 42 claims = {len(runs) * 42} calls "
          f"({sum(1 for r in runs if r[0] == 'llm') * 42} to OpenRouter)\n")
    by = defaultdict(float)
    for system, model, arm, label, cost in lines:
        by[(model, arm)] += cost
    for (model, arm), cost in sorted(by.items()):
        n = sum(1 for r in runs if r[1] == model and r[2] == arm)
        print(f"  {model:<32} {arm:<7} x{n}   ${cost:.4f}")
    raw = sum(c for *_, c in lines)
    print(f"\nProjected: ${raw:.2f}, ${projected:.2f} with {SAFETY:.2f}x headroom. "
          f"Cap ${CAP_USD:.2f}.")
    return projected


def _one(run):
    system, model, arm, label = run
    flag = "--jev-model" if system == "jev" else "--llm-model"
    cmd = [PY, "run.py", "--system", system, flag, model, "--arm", arm, "--label", label]
    res = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    wrote = [ln for ln in res.stdout.splitlines() if ln.startswith("wrote ")]
    tail = wrote[-1] if wrote else "(wrote nothing)"
    return run, res.returncode, tail, res.stderr[-500:]


def cmd_run():
    projected = cmd_plan()
    if projected > CAP_USD:
        sys.exit(f"\nSTOP: projection ${projected:.2f} exceeds the ${CAP_USD:.2f} cap.")
    runs = plan()
    # One serial queue per (system, model), the queues in parallel: no provider sees more
    # than one request at a time from this harness, same as every earlier run.
    queues = defaultdict(list)
    for r in runs:
        queues[(r[0], r[1])].append(r)

    def drain(q):
        return [_one(r) for r in q]

    with ThreadPoolExecutor(max_workers=len(queues)) as pool:
        for results in pool.map(drain, queues.values()):
            for run, code, tail, err in results:
                print(f"{'ok ' if code == 0 else 'ERR'} {run}  {tail}")
                if code:
                    print(err)


# ------------------------------------------------------------------ analysis

def files(system, model, label_prefix):
    """Output files for one group, ordered by repeat index."""
    stem = f"{system}-{slug(model)}-{label_prefix}-r"
    found = sorted(glob.glob(str(RESULTS / f"{stem}*.jsonl")))
    return [pathlib.Path(f).relative_to(HERE).as_posix() for f in found]


def right(r):
    return r.get("predicted") == r["label"]


def acc(rows, tier=None):
    sub = [r for r in rows if tier is None or r["tier"] == tier]
    return sum(right(r) for r in sub) / len(sub)


def as_map(rows):
    return {r["id"]: r for r in rows}


def spread(runs, tier=None):
    vals = [acc(r, tier) for r in runs]
    return sum(vals) / len(vals), min(vals), max(vals)


def pc(x):
    return f"{x * 100:.1f}%"


def majority_right(runs):
    """Per claim: right in at least 3 of 5 runs (or of however many runs there are)."""
    maps = [as_map(r) for r in runs]
    ids = maps[0].keys()
    return {i: sum(right(m[i]) for m in maps) * 2 > len(maps) for i in ids}


def times_right(runs):
    maps = [as_map(r) for r in runs]
    return {i: sum(right(m[i]) for m in maps) for i in maps[0]}


def mcnemar_maps(a, b, ids):
    """a, b: {id: bool right}. Returns (a-only-right, b-only-right, exact p)."""
    x = sum(1 for i in ids if a[i] and not b[i])
    y = sum(1 for i in ids if b[i] and not a[i])
    return x, y, exact_two_sided(x, y)


def determinism(runs):
    """Rows whose label, confidence or probabilities differ across identical-input runs."""
    maps = [as_map(r) for r in runs]
    ids = list(maps[0])
    label_diff, conf_diff, prob_diff, max_conf_gap = [], [], [], 0.0
    for i in ids:
        rs = [m[i] for m in maps]
        if len({r.get("predicted") for r in rs}) > 1:
            label_diff.append(i)
        confs = [r.get("confidence") for r in rs]
        if len(set(confs)) > 1:
            conf_diff.append(i)
            max_conf_gap = max(max_conf_gap, max(confs) - min(confs))
        key = "probabilities" if "probabilities" in rs[0] else "nouls"
        if len({json.dumps(r.get(key), sort_keys=True) for r in rs}) > 1:
            prob_diff.append(i)
    return label_diff, conf_diff, prob_diff, max_conf_gap


def jev_cost(rows):
    return sum(r["input_tokens"] for r in rows) / len(rows) / 1e6 * JEV_PER_MTOK


def cmd_analyse():
    groups = {
        "Jev jev-latest": files("jev", "jev-latest", "t4"),
        "Jev jev-1.13.0": files("jev", "jev-1.13.0", "t4pin"),
    }
    for m in LLMS:
        groups[LLM_NAMES[m]] = files("llm", m, "t4")
    arms = {
        "Jev split": files("jev", "jev-latest", "t3b"),
        "Jev fan-out": files("jev", "jev-latest", "t3c"),
    }
    for m in LLMS:
        arms[f"{LLM_NAMES[m]} split"] = files("llm", m, "t3b")

    missing = [k for k, v in {**groups, **arms}.items() if not v]
    if missing:
        sys.exit(f"no result files yet for: {', '.join(missing)}")

    data = {k: [load(f) for f in v] for k, v in {**groups, **arms}.items()}
    errors = {k: sum(1 for run in v for r in run if r.get("error")) for k, v in data.items()}
    ref = {"Jev jev-latest": BASE_FILES["jev"],
           **{LLM_NAMES[m]: BASE_FILES[m] for m in LLMS}}

    print("# Tests 3 and 4, analysis\n")
    print("Files:")
    for k, v in {**groups, **arms}.items():
        print(f"  {k}: " + ", ".join(pathlib.Path(f).name for f in v))
    print("\nFailed calls: " + ", ".join(f"{k} {n}" for k, n in errors.items()))
    served = defaultdict(set)
    for k, runs in data.items():
        for run in runs:
            for r in run:
                if r.get("served_model"):
                    served[k].add(r["served_model"])
    for k, v in served.items():
        print(f"  served model, {k}: {', '.join(sorted(v))}")

    # ---------------------------------------------------------------- Test 4
    print("\n## Test 4: five runs each, schema-only\n")
    print("| system | all 42 mean (min to max) | easy 24 | hard 18 | 20 Sep single run, hard 18 |")
    print("|---|---|---|---|---|")
    for k in groups:
        cells = []
        for tier in (None, "B", "A"):
            mean, lo, hi = spread(data[k], tier)
            cells.append(f"{pc(mean)} ({pc(lo)} to {pc(hi)})")
        r20 = pc(acc(load(ref[k]), "A")) if k in ref else "n/a"
        print(f"| {k} | " + " | ".join(cells) + f" | {r20} |")

    print("\nPer-run hard-18 accuracy:")
    for k in groups:
        print(f"  {k:<16} " + "  ".join(pc(acc(r, 'A')) for r in data[k]))

    print("\nPer claim: how many of five runs got it right\n")
    ids = [r["id"] for r in data["Jev jev-latest"][0]]
    meta = as_map(data["Jev jev-latest"][0])
    tr = {k: times_right(data[k]) for k in groups}
    print("| claim | tier | label | " + " | ".join(groups) + " |")
    print("|---|---|---|" + "---|" * len(groups))
    for i in ids:
        print(f"| {i} | {meta[i]['tier']} | {meta[i]['label']} | "
              + " | ".join(str(tr[k][i]) for k in groups) + " |")
    unstable = {k: [i for i in ids if 0 < tr[k][i] < REPEATS] for k in groups}
    print("\nClaims not unanimous across the five runs:")
    for k, v in unstable.items():
        print(f"  {k}: {len(v)}  {', '.join(v)}")

    print("\n### Jev determinism, identical input five times\n")
    for k in ["Jev jev-latest", "Jev jev-1.13.0", "Jev split", "Jev fan-out"]:
        ld, cd, pd, gap = determinism(data[k])
        print(f"  {k}: label differs on {len(ld)} of 42, confidence on {len(cd)}, "
              f"distribution on {len(pd)}; largest confidence gap {gap:.2f}"
              + (f"  [{', '.join(sorted(set(ld + cd + pd)))}]" if ld or cd or pd else ""))

    print("\n### The headline: Jev's lead on the hard 18 across the spread\n")
    jmean, jlo, jhi = spread(data["Jev jev-latest"], "A")
    llm_stats = {LLM_NAMES[m]: spread(data[LLM_NAMES[m]], "A") for m in LLMS}
    best_mean = max(v[0] for v in llm_stats.values())
    best_max = max(v[2] for v in llm_stats.values())
    print(f"  Jev mean {pc(jmean)} (min {pc(jlo)}, max {pc(jhi)})")
    for n, (mn, lo, hi) in llm_stats.items():
        print(f"  {n}: mean {pc(mn)} (min {pc(lo)}, max {pc(hi)}); "
              f"Jev lead on means {(jmean - mn) * 100:+.1f} points")
    if jlo > best_max:
        verdict = "SURVIVES: Jev's worst run beats every frontier model's best run"
    elif jmean > best_mean:
        verdict = "SHRINKS: Jev's mean still leads, but the run ranges overlap"
    else:
        verdict = "VANISHES: a frontier model's mean hard-18 accuracy equals or beats Jev's"
    print(f"  Pre-registered reading: {verdict}")

    jmaj = majority_right(data["Jev jev-latest"])
    hard = [i for i in ids if meta[i]["tier"] == "A"]
    print("\n  Exact McNemar, majority-of-five correctness, hard 18, Jev vs each:")
    for m in LLMS:
        n = LLM_NAMES[m]
        x, y, p = mcnemar_maps(jmaj, majority_right(data[n]), hard)
        pair_ps = []
        for a, b in zip(data["Jev jev-latest"], data[n]):
            am = {r["id"]: right(r) for r in a}
            bm = {r["id"]: right(r) for r in b}
            pair_ps.append(mcnemar_maps(am, bm, hard)[2])
        print(f"    Jev vs {n}: Jev-only-right {x}, {n}-only-right {y}, p = {p:.3f}; "
              f"run-by-run p from {min(pair_ps):.3f} to {max(pair_ps):.3f}")

    # ---------------------------------------------------------------- Test 3
    print("\n## Test 3: one change per arm, against its own baseline\n")
    base = data["Jev jev-latest"]
    bmean, blo, bhi = spread(base)
    bmaj = majority_right(base)

    def arm_line(name, runs, base_runs):
        mean, lo, hi = spread(runs)
        hmean, hlo, hhi = spread(runs, "A")
        b_mean, b_lo, b_hi = spread(base_runs)
        bm = majority_right(base_runs)
        am = majority_right(runs)
        x, y, p = mcnemar_maps(bm, am, ids)
        xh, yh, ph = mcnemar_maps(bm, am, hard)
        outside = mean < b_lo or mean > b_hi
        if outside and p < 0.05:
            reading = "QUESTION DESIGN MATTERS: outside the baseline's spread and p < 0.05"
        elif outside:
            reading = "moved beyond run-to-run noise, not significant"
        else:
            reading = "no detectable effect: inside the baseline's own spread"
        print(f"  {name}: all 42 {pc(mean)} ({pc(lo)} to {pc(hi)}), hard 18 {pc(hmean)} "
              f"({pc(hlo)} to {pc(hhi)}); baseline all 42 {pc(b_mean)} ({pc(b_lo)} to "
              f"{pc(b_hi)})")
        print(f"    McNemar all 42: baseline-only-right {x}, arm-only-right {y}, p = {p:.3f}. "
              f"Hard 18: {xh} and {yh}, p = {ph:.3f}")
        print(f"    Pre-registered reading: {reading}")

    print("(a) Pin the version, jev-1.13.0 against jev-latest")
    arm_line("Jev jev-1.13.0", data["Jev jev-1.13.0"], base)
    same = all(as_map(a)[i].get("probabilities") == as_map(b)[i].get("probabilities")
               for a, b in zip(base, data["Jev jev-1.13.0"]) for i in ids)
    print(f"    Identical distributions run for run, latest vs pinned: {same}")
    r20 = as_map(load(BASE_FILES["jev"]))
    moved = [i for i in ids if r20[i]["predicted"] != as_map(base[0])[i]["predicted"]]
    print(f"    20 Sep jev-latest vs today's jev-latest run 1, labels that differ: "
          f"{len(moved)} {moved}")

    print("\n(b) Split the compound label")
    arm_line("Jev split", data["Jev split"], base)
    for m in LLMS:
        n = LLM_NAMES[m]
        arm_line(f"{n} split (one run)", data[f"{n} split"], data[n])
    print("\n  The four boundary rows Test 2 named. Times right of five, schema-only; "
          "then the split arm's raw answer:")
    for i in BOUNDARY_ROWS:
        cells = [f"Jev {tr['Jev jev-latest'][i]}/5 -> "
                 + "/".join(sorted({as_map(r)[i].get('predicted_raw') for r in data['Jev split']}))]
        for m in LLMS:
            n = LLM_NAMES[m]
            cells.append(f"{n} {tr[n][i]}/5 -> {as_map(data[n + ' split'][0])[i].get('predicted_raw')}")
        print(f"    {i} (label {meta[i]['label']}): " + "; ".join(cells))
    print("\n  Split arm, how the four-way answers fell against the true label:")
    for k in ["Jev split"] + [f"{LLM_NAMES[m]} split" for m in LLMS]:
        tally = defaultdict(int)
        for run in data[k]:
            for r in run:
                tally[(r["label"], r.get("predicted_raw"))] += 1
        print(f"    {k}: " + ", ".join(f"{lab}->{raw} {n}" for (lab, raw), n in sorted(
            tally.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))))

    print("\n(c) Multi-question fan-out")
    arm_line("Jev fan-out", data["Jev fan-out"], base)
    c_base = sum(jev_cost(r) for r in base) / len(base)
    c_fan = sum(jev_cost(r) for r in data["Jev fan-out"]) / len(data["Jev fan-out"])
    s_base = sum(r["seconds"] for run in base for r in run) / (42 * len(base))
    s_fan = sum(r["seconds"] for run in data["Jev fan-out"] for r in run) / (42 * REPEATS)
    t_base = sum(r["input_tokens"] for run in base for r in run) / (42 * len(base))
    t_fan = sum(r["input_tokens"] for run in data["Jev fan-out"] for r in run) / (42 * REPEATS)
    print(f"    cost per claim: single Choice ${c_base:.6f}, fan-out ${c_fan:.6f} "
          f"({c_fan / c_base:.2f}x); input tokens {t_base:.0f} vs {t_fan:.0f}; "
          f"seconds {s_base:.2f} vs {s_fan:.2f}")

    # ---------------------------------------------------------------- spend
    print("\n## Spend\n")
    total = 0.0
    for k, runs in data.items():
        if k.startswith("Jev"):
            s = sum(jev_cost(r) * len(r) for r in runs)
        else:
            s = sum(x.get("charged_usd") or 0 for r in runs for x in r)
        total += s
        print(f"  {k:<22} ${s:.4f}")
    print(f"  total                  ${total:.4f}  (cap ${CAP_USD:.2f})")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    {"plan": cmd_plan, "run": cmd_run, "analyse": cmd_analyse}.get(
        cmd, lambda: sys.exit(__doc__))()


if __name__ == "__main__":
    main()
