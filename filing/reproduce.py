#!/usr/bin/env python3
"""Recompute the figures in the three filing verdicts from the reduced runs. No keys.
(The pool size, per-folder pool counts and hashes come from data/frozen-facts.json: the pool
itself is private, so those cannot be recomputed here.)

    python3 filing/reproduce.py        # exits 0 only if everything matches

1. Copies runs/ and data/ into a temporary folder and runs the four scoring scripts in
   code/ (analyse.py, describe.py, analyse1b.py, analyse1c.py) there, unchanged. Two things
   in them read private files, and those reads are pointed at the reduced files instead:
   test1b_neighbours.load/sha (the Test 1b neighbour list and the pool, for near-duplicate
   ids, the pool size and the hashes) and analyse1c's read of the held-out neighbour list.
   The reduced files keep, per neighbour, only its rank, its folder, its near-duplicate flag
   and, if it is itself a test note, that note's id.
2. Compares the four regenerated summaries byte for byte with summaries/, which are the
   private summaries as the tests wrote them (titles and paths withheld in the descriptive one).
3. Checks the figures the verdicts quote that are not a field in a summary: counts by
   folder, note ids, cost ratios, and the like. Each is recomputed here and compared with
   the number printed in the verdict.

Standard library only.
"""

import contextlib
import importlib
import io
import json
import math
import pathlib
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
SUMMARIES = ("routing-summary.json", "routing-descriptive.json", "test1b-summary.json",
             "test1c-summary.json")
failures = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok ' if ok else 'BAD'} {name}: {got}" + ("" if ok else f" (verdict says {want})"))
    if not ok:
        failures.append(name)


def jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def regenerate(tmp):
    results, data = tmp / "results", tmp / "data"
    shutil.copytree(HERE / "runs", results)
    shutil.copytree(HERE / "data", data)
    facts = json.loads((data / "frozen-facts.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(HERE / "code"))

    import analyse
    analyse.RESULTS = results                       # analyse1b/1c read it at import

    nb = importlib.import_module("test1b_neighbours")
    nb.DATA, nb.NEIGHBOURS, nb.POOL = data, data / "test1b-neighbours.jsonl", \
        data / "test1b-pool.jsonl"                  # the pool itself is not published
    real_load = nb.load
    nb.load = lambda p: ([None] * facts["pool_notes"] if pathlib.Path(p) == nb.POOL
                         else real_load(p))
    hashes = {h["file"]: h["sha256"] for h in facts["sha256"]}
    nb.sha = lambda p: hashes[pathlib.Path(p).name]

    import describe
    describe.RESULTS, describe.DATA = results, data
    import analyse1b
    import analyse1c

    with contextlib.redirect_stdout(io.StringIO()):
        for mod in (analyse, describe):
            sys.argv = [mod.__name__, "routing"]
            mod.main()
        analyse1b.main()
        analyse1c.main()
    return results


def main():
    with tempfile.TemporaryDirectory() as t:
        results = regenerate(pathlib.Path(t))
        print("Summaries regenerated from the reduced runs, compared byte for byte:")
        for name in SUMMARIES:
            same = (results / name).read_bytes() == (HERE / "summaries" / name).read_bytes()
            check(name, "identical" if same else "DIFFERS", "identical")
        verdict_figures(results)
    if failures:
        print(f"FAIL: {len(failures)} mismatch(es): {', '.join(failures)}")
        sys.exit(1)
    print("OK: every summary and every checked verdict figure matches.")


def verdict_figures(results):
    s1 = json.loads((results / "routing-summary.json").read_text())
    d1 = json.loads((results / "routing-descriptive.json").read_text())
    s1b = json.loads((results / "test1b-summary.json").read_text())
    s1c = json.loads((results / "test1c-summary.json").read_text())
    key = {r["id"]: r["label"] for r in jsonl(HERE / "data/routing-key.jsonl")}
    held = {r["id"]: r["label"] for r in jsonl(HERE / "data/test1c-heldout.jsonl")}
    runs = lambda pat: [jsonl(p) for p in sorted(results.glob(pat))]

    def by_home(ids, labels):
        return dict(sorted(Counter(labels[i] for i in ids).items()))

    print("\nTest 1 verdict:")
    j, l = s1["systems"]["jev"], s1["systems"]["llm"]
    check("Claude cost per item / Jev's, rounded", round(l["cost_per_item_usd"] / j["cost_per_item_usd"]), 84)
    claude_only = sorted(set(l["majority_right"]) - set(j["majority_right"]))
    content = [i for i in claude_only if key[i] == "content"]
    check("Claude-only right, content notes", content,
          ["r-041", "r-042", "r-043", "r-045", "r-048", "r-051"])
    jev_only = sorted(set(j["majority_right"]) - set(l["majority_right"]))
    check("Jev-only right, with folders", [(i, key[i]) for i in jev_only],
          [("r-029", "income-bridge"), ("r-031", "books")])
    for sysname, cut, exact, want in (("jev", 1.0, True, (56, 10)), ("jev", 0.98, False, (118, 10)),
                                      ("llm", 0.98, True, (13, 3)), ("llm", 0.9, False, (91, 10))):
        rows = [r for rs in runs(f"routing-{sysname}-r*.jsonl") for r in rs
                if (round(r["confidence"], 2) == cut if exact else r["confidence"] >= cut)]
        check(f"{sysname} answers {'at' if exact else 'at or above'} {cut}, and wrong",
              (len(rows), sum(r["predicted"] != r["label"] for r in rows)), want)
    ce = d1["jev"]["confident_errors"]
    check("Jev confidently wrong notes, and those wrong in all 5 runs",
          (len({e['id'] for e in ce}), sum(e["runs"] == 5 for e in ce)), (9, 7))

    print("\nTest 1b verdict:")
    a = s1b["arms"]
    check("D cost per item / B's, rounded", round(a["D"]["cost_per_item_usd"] / a["B"]["cost_per_item_usd"]), 76)
    mr = {k: set(v["majority_right"]) for k, v in a.items()}
    check("B right, C wrong, by folder", by_home(mr["B"] - mr["C"], key),
          {"books": 1, "content": 3, "efformism": 3, "mission-control": 3, "reference": 4})
    check("C right, B wrong, by folder", by_home(mr["C"] - mr["B"], key),
          {"income-bridge": 2, "knowledge": 2, "reference": 3})
    check("D right, B wrong", sorted(mr["D"] - mr["B"]), ["r-020", "r-022", "r-033", "r-062", "r-063"])
    check("B right, D wrong", sorted(mr["B"] - mr["D"]), [])
    check("B right, A wrong, by folder", by_home(mr["B"] - mr["A"], key),
          {"content": 6, "efformism": 1, "income-bridge": 5, "knowledge": 1, "mission-control": 1,
           "reference": 4})
    check("efformism notes right: C, B", (len({i for i in mr["C"] if key[i] == "efformism"}),
                                          len({i for i in mr["B"] if key[i] == "efformism"})), (1, 4))
    check("B content answers right, of 75", a["B"]["confusion"]["content"].get("content"), 70)
    check("B confident-error notes", a["B"]["high_conf_error_ids"], ["r-003", "r-046", "r-080"])
    check("D confident-error notes", a["D"]["high_conf_error_ids"], ["r-003", "r-034", "r-046", "r-080"])
    check("B answers at 1.00, wrong", (a["B"]["answers_at_confidence_1"], a["B"]["wrong_at_confidence_1"]), (20, 5))
    ties = sorted(r["id"] for rs in runs("test1b-C-r*.jsonl") for r in rs if r["tie_broken_by_score"])
    check("arm C ties broken by score", ties, ["r-007", "r-020", "r-036", "r-044", "r-047"])
    check("near-duplicate notes", s1b["neighbours"]["near_duplicate_ids"], ["r-029", "r-042", "r-047", "r-048"])
    n = s1b["neighbours"]
    check("neighbour slots with the note's own label", (n["neighbour_homes_matching_label"], n["neighbour_slots"]), (509, 830))
    check("pool notes by folder", json.loads((HERE / "data/frozen-facts.json").read_text())["pool_per_home"],
          {"books": 4, "content": 103, "efformism": 4, "income-bridge": 82, "knowledge": 253,
           "mission-control": 86, "reference": 73})
    check("cost of arm B runs, arm D runs", (round(a["B"]["cost_total_usd"], 3), round(a["D"]["cost_total_usd"], 2)), (0.049, 3.76))

    print("\nTest 1c verdict:")
    c = s1c["arms"]
    esc = s1c["escalation_jev_to_claude"]["B"]
    check("escalation (B) cost / D cost, as a percentage", round(100 * esc["cost_per_item_usd"] / c["D"]["cost_per_item_usd"]), 37)
    six = c["B"]["kept_wrong_ids"]
    check("B's confidently wrong notes", six, ["h-023", "h-028", "h-030", "h-042", "h-044", "h-075"])
    d_runs = runs("test1c-D-r*.jsonl")
    b_runs = runs("test1c-B-r*.jsonl")

    def maj(rs):
        votes = defaultdict(Counter)
        for run in rs:
            for r in run:
                votes[r["id"]][r["predicted"]] += 1
        return {i: v.most_common(1)[0][0] for i, v in votes.items() if v.most_common(1)[0][1] >= 3}

    md, mb = maj(d_runs), maj(b_runs)
    check("the six: folder, Jev's and Claude's majority answer", [(i, held[i], mb[i], md.get(i)) for i in six],
          [("h-023", "income-bridge", "reference", "reference"),
           ("h-028", "income-bridge", "reference", "reference"),
           ("h-030", "income-bridge", "mission-control", "mission-control"),
           ("h-042", "content", "knowledge", "knowledge"),
           ("h-044", "content", "mission-control", "mission-control"),
           ("h-075", "reference", "mission-control", "mission-control")])
    check("Claude runs right on h-028", sum(r["predicted"] == r["label"] for rs in d_runs for r in rs if r["id"] == "h-028"), 2)
    check("of the six, Claude sure and wrong on", sorted(set(six) & set(c["D"]["kept_wrong_ids"])), ["h-023", "h-042", "h-044"])
    er, br = set(esc["majority_right"]), set(c["B"]["majority_right"])
    check("escalation fixed", sorted(er - br), ["h-012", "h-039", "h-070"])
    check("escalation broke", sorted(br - er), ["h-038", "h-055"])
    check("escalation right, Jev alone right, of 75", (len(er), len(br)), (65, 64))
    check("escalation and Claude right on the same notes", er == set(c["D"]["majority_right"]), True)
    f_rows = [r for rs in runs("test1c-F-r*.jsonl") for r in rs if not r["keep"]]
    check("F passes, and those with no yes at 0.80",
          (len(f_rows), sum(r["confidence"] < 0.80 for r in f_rows)), (214, 206))
    seen = {x["test_note_id"] for r in jsonl(HERE / "data/test1b-neighbours.jsonl")
            for x in r["neighbours"] if (x["test_note_id"] or "").startswith("h-")}
    check("held-out notes shown as examples to working-set notes", len(seen), 54)
    check("one-sided 95% bound on disagreement, %", round(100 * (1 - 0.05 ** (1 / 75)), 1), 3.9)
    w = s1c["working_set_rounds_description_only"]
    wr = {(v["shape"], k.split("-")[3]): v["agree"] for k, v in w.items()}
    check("W rounds: yes/no round 0, one-question rounds 1-2, yes/no rounds 1-2",
          (wr[("nouls", "round0")], wr[("choice", "round1")], wr[("choice", "round2")],
           wr[("nouls", "round1")], wr[("nouls", "round2")]), (70, 73, 74, 72, 72))
    w2 = jsonl(next(results.glob("test1c-W-B-round2-*.jsonl")))
    still = sorted(r["id"] for r in w2 if r["predicted"] != r["label"])
    check("W notes still wrong after round 2, incl. r-003 and r-071",
          (len(still), {"r-003", "r-071"} <= set(still)), (9, True))
    check("held-out answers scored", sum(v["calls"] for v in c.values()), 1575)
    spend_w = sum(r["cost_usd"] for p in results.glob("test1c-W-*.jsonl") for r in jsonl(p))
    spend_j = sum(c[x]["cost_total_usd"] for x in "BFG")
    check("spend: Claude held-out, Jev arms, W rounds, total",
          (round(c["D"]["cost_total_usd"], 2), round(spend_j, 2), round(spend_w, 2),
           round(c["D"]["cost_total_usd"] + spend_j + spend_w, 2)), (3.41, 0.15, 0.06, 3.61))
    check("near-duplicate held-out notes", s1c["near_duplicate_ids"], ["h-035", "h-040"])
    check("Jev -> me, kept and wrong of 375 calls: B, F, G",
          tuple(c[x]["kept_wrong"] for x in "BFG"), (30, 15, 22))


if __name__ == "__main__":
    main()
