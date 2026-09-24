#!/usr/bin/env python3
"""Check the Test 1b examples (T-818). Exits 0 only if every check passes.

    python3 check_test1b_neighbours.py                     # Test 1b: the 83 key notes
    python3 check_test1b_neighbours.py --test1c            # Test 1c: the 75 held-out notes

1. data/test1b-neighbours.jsonl has one row per key note, in key order, all 83.
2. Every note has exactly 10 neighbours, ranked 1..10, scores non-increasing.
3. No note is its own neighbour, and no neighbour appears twice for one note.
4. Every neighbour is in the frozen pool with the same home, and its example text is the
   first 500 characters of that pool note's text.
5. Rebuilding from the frozen pool, twice, gives output byte-identical to the saved file.
"""

import json
import sys

import test1b_neighbours as nb

failures = []


def check(ok, msg):
    if not ok:
        failures.append(msg)


def main():
    if "--test1c" in sys.argv:
        key_path, nbr_path, expected = (nb.DATA / "test1c-heldout.jsonl",
                                        nb.DATA / "test1c-neighbours.jsonl", 75)
    else:
        key_path, nbr_path, expected = nb.KEY, nb.NEIGHBOURS, 83
    key = nb.load(key_path)
    pool = {p["path"]: p for p in nb.load(nb.POOL)}
    saved = nbr_path.read_text(encoding="utf-8")
    rows = [json.loads(l) for l in saved.splitlines()]

    check(len(key) == expected, f"key has {len(key)} notes, expected {expected}")
    check([r["id"] for r in rows] == [k["id"] for k in key], "rows do not match key order")
    for r, k in zip(rows, key):
        n = r["neighbours"]
        check(r["path"] == k["path"] and r["label"] == k["label"], f"{r['id']}: path/label")
        check(len(n) == nb.K, f"{r['id']}: {len(n)} neighbours")
        check([x["rank"] for x in n] == list(range(1, nb.K + 1)), f"{r['id']}: ranks")
        check(all(a["score"] >= b["score"] for a, b in zip(n, n[1:])), f"{r['id']}: order")
        paths = [x["path"] for x in n]
        check(k["path"] not in paths, f"{r['id']} is its own neighbour")
        check(len(set(paths)) == len(paths), f"{r['id']}: duplicate neighbour")
        for x in n:
            p = pool.get(x["path"])
            check(p is not None, f"{r['id']}: {x['path']} not in pool")
            if p:
                check(p["home"] == x["home"], f"{r['id']}: {x['path']} home")
                check(p["text"][:nb.EXAMPLE_CHARS] == x["text"], f"{r['id']}: {x['path']} text")

    pool_rows, key_rows = nb.load(nb.POOL), nb.load(key_path)
    first = nb.serialise(nb.compute(pool_rows, key_rows))
    second = nb.serialise(nb.compute(pool_rows, key_rows))
    check(first == second, "two rebuilds differ")
    check(first == saved, f"rebuild differs from {nbr_path.name}")
    if "--test1c" in sys.argv:
        used = {k["path"] for k in nb.load(nb.KEY)}
        check(not any(k["path"] in used for k in key_rows), "held-out overlaps Test 1 notes")

    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for f in failures[:50]:
            print("  " + f)
        sys.exit(1)
    print(f"OK: {len(rows)} notes x {nb.K} neighbours, none its own, rebuild identical "
          f"(pool {len(pool)} notes, sha256 {nb.sha(nb.POOL)[:12]}, "
          f"neighbours sha256 {nb.sha(nbr_path)[:12]})")


if __name__ == "__main__":
    main()
