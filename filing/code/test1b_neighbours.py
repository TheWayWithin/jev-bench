#!/usr/bin/env python3
"""Test 1b (T-818): the labelled examples, built before any model is called.
Pre-registration: test1b-preregistration.md ("The examples").

    python3 test1b_neighbours.py snapshot   # scan the vault -> data/test1b-pool.jsonl
    python3 test1b_neighbours.py build      # pool file -> data/test1b-neighbours.jsonl

The vault keeps changing, so the pool is frozen to a file first and the neighbours are
computed only from that file. Anyone rerunning `build` gets byte-identical output;
check_test1b_neighbours.py proves it. Standard library only.

Retrieval, as pre-registered: BM25, k1 = 1.5, b = 0.75, lower-cased word tokens
(`\\w+`), documents and queries are title + first 1,500 characters (the same text Test 1
showed the models, from build_keys.item_text). k = 10, leave one out by path.

Choices the pre-registration leaves open, fixed here before any model call:
- idf = ln((N - df + 0.5) / (df + 0.5) + 1), the non-negative (Lucene) form; N is the
  whole pool, the test note included.
- each distinct query term counts once (no query-term-frequency weight).
- ranking ties break on path, ascending, so the order never depends on the file system.
- near-duplicate: a neighbour whose word-token set has Jaccard similarity >= 0.5 with the
  test note's, over the same title + 1,500 characters. First set at 0.8; that counted
  none, yet two pairs of versions of one note scored 0.70 and 0.78. [Redacted for
  publication, 24 Sep 2026: what the notes were.] The top values run 0.78, 0.70, 0.70, 0.61, then 0.40, so 0.5 sits at the break. Changed
  on 24 Sep after reading the similarity values and before any Test 1b model call.
"""

import hashlib
import json
import math
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_keys  # noqa: E402  (HOMES, eligible, item_text: the Test 1 rules)

DATA = HERE / "data"
KEY = DATA / "routing-key.jsonl"
POOL = DATA / "test1b-pool.jsonl"
NEIGHBOURS = DATA / "test1b-neighbours.jsonl"
K = 10
K1, B = 1.5, 0.75
EXAMPLE_CHARS = 500
NEAR_DUP_JACCARD = 0.5
TOKEN = re.compile(r"\w+")


def tokens(s):
    return TOKEN.findall(s.lower())


def doc_text(title, text):
    return f"{title}\n{text}"


# ------------------------------------------------------------------ snapshot

def snapshot():
    rows = []
    for label, folders in build_keys.HOMES.items():
        paths = sorted({p for f in folders for p in (build_keys.VAULT / f).rglob("*.md")
                        if build_keys.eligible(label, p)})
        for p in paths:
            title, text = build_keys.item_text(p)
            rows.append({"path": str(p.relative_to(build_keys.VAULT)), "home": label,
                         "title": title, "text": text})
    rows.sort(key=lambda r: r["path"])
    with open(POOL, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    key = load(KEY)
    pool_paths = {r["path"] for r in rows}
    missing = [k["id"] for k in key if k["path"] not in pool_paths]
    print(json.dumps({"pool": len(rows),
                      "per_home": dict(Counter(r["home"] for r in rows)),
                      "test_notes_missing_from_pool": missing,
                      "sha256": sha(POOL)}, indent=2))


# ------------------------------------------------------------------ BM25

def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


class BM25:
    def __init__(self, docs):
        self.tf = [Counter(tokens(d)) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.n = len(docs)
        self.avg = sum(self.len) / self.n
        df = Counter(t for c in self.tf for t in c)
        self.idf = {t: math.log((self.n - d + 0.5) / (d + 0.5) + 1) for t, d in df.items()}

    def score(self, query_terms, i):
        tf, dl = self.tf[i], self.len[i]
        s = 0.0
        for t in query_terms:
            f = tf.get(t)
            if f:
                s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avg))
        return s


def jaccard(a, b):
    a, b = set(tokens(a)), set(tokens(b))
    return len(a & b) / len(a | b) if a | b else 0.0


def compute(pool, key):
    """Return the neighbour rows as a list of dicts, deterministically."""
    docs = [doc_text(p["title"], p["text"]) for p in pool]
    index = BM25(docs)
    out = []
    for k in key:
        q_text = doc_text(k["title"], k["text"])
        q = sorted(set(tokens(q_text)))
        scored = [(index.score(q, i), pool[i]["path"], i) for i in range(len(pool))
                  if pool[i]["path"] != k["path"]]
        scored.sort(key=lambda x: (-x[0], x[1]))
        nbrs = []
        for rank, (s, path, i) in enumerate(scored[:K], 1):
            p = pool[i]
            j = jaccard(q_text, docs[i])
            nbrs.append({"rank": rank, "path": path, "home": p["home"], "score": s,
                         "jaccard": round(j, 4), "near_duplicate": j >= NEAR_DUP_JACCARD,
                         "title": p["title"], "text": p["text"][:EXAMPLE_CHARS]})
        out.append({"id": k["id"], "path": k["path"], "label": k["label"],
                    "neighbours": nbrs})
    return out


def serialise(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def build():
    pool, key = load(POOL), load(KEY)
    text = serialise(compute(pool, key))
    NEIGHBOURS.write_text(text, encoding="utf-8")
    rows = [json.loads(l) for l in text.splitlines()]
    dups = [r["id"] for r in rows if any(n["near_duplicate"] for n in r["neighbours"])]
    print(json.dumps({"items": len(rows), "pool": len(pool), "pool_sha256": sha(POOL),
                      "neighbours_sha256": sha(NEIGHBOURS),
                      "test_notes_with_near_duplicate_neighbour": len(dups),
                      "near_duplicate_ids": dups}, indent=2))


if __name__ == "__main__":
    {"snapshot": snapshot, "build": build}[sys.argv[1]]()
