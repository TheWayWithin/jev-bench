#!/usr/bin/env python3
"""Leak check for the published filing tests. Exits 0 only if nothing private is found.

    python3 filing/check_public.py --private-dir <folder holding the private data files>

Only someone who holds the private files can run this: the answer key
(routing-key.jsonl), the held-out set (test1c-heldout.jsonl) and the pool
(test1b-pool.jsonl), and the ideas queue (ideas-items.jsonl) if present. Everything they
contain about each note becomes a thing to search for:

- its path, its filename and its filename without `.md` (8 characters or more);
- its title;
- every 40-character run of its text.

Every file under filing/, plus the repository README, is searched for all of them,
case-insensitive and with runs of whitespace collapsed to one space. `--deny FILE` adds
extra terms, one per line, for anything private that is not in those files (a person's
name, say); keep that file private too.

Three things are not counted as a leak, and each is printed so it can be checked:
- a title or filename that is one plain word (`summary`, `about`, a folder name such as
  `efformism`): one common word identifies no note;
- a term or run of text that is already public in the README on origin/main, which is where
  some notes quote the author's own published words and name;
- the terms in PUBLIC below, with the reason given.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
WINDOW = 40
MIN_STEM = 8
WS = re.compile(r"\s+")
LONE_WORD = re.compile(r"[a-z]+")
PUBLIC = {
    "the way within": "the author's published book, named in the routing prompt as it was run",
}


def norm(s):
    return WS.sub(" ", s).lower()


def published_files():
    files = [p for p in sorted(HERE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    return files + [HERE.parent / "README.md"]


def needles(private):
    terms, windows = {}, set()
    for name in ("routing-key.jsonl", "test1c-heldout.jsonl", "test1b-pool.jsonl",
                 "ideas-items.jsonl"):
        path = private / name
        if not path.exists():
            if name == "ideas-items.jsonl":
                continue
            sys.exit(f"missing private file: {path}")
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if "path" in r:
                p = pathlib.PurePosixPath(r["path"])
                terms[norm(r["path"])] = "path"
                terms[norm(p.name)] = "filename"
                if len(p.stem) >= MIN_STEM:
                    terms[norm(p.stem)] = "filename stem"
            for field in ("title", "proposal", "source"):
                if r.get(field):
                    terms[norm(r[field])] = field
            text = norm(r.get("text", ""))
            windows.update(text[i:i + WINDOW] for i in range(len(text) - WINDOW + 1))
    return terms, windows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True, type=pathlib.Path)
    ap.add_argument("--deny", type=pathlib.Path)
    args = ap.parse_args()
    terms, windows = needles(args.private_dir)
    if args.deny:
        for t in args.deny.read_text(encoding="utf-8").splitlines():
            if t.strip():
                terms[norm(t.strip())] = "deny list"
    already_public = norm(subprocess.run(
        ["git", "-C", str(HERE.parent), "show", "origin/main:README.md"],
        capture_output=True, text=True, check=True).stdout)
    hits, exempt = [], set()
    files = published_files()
    for f in files:
        text = norm(f.read_text(encoding="utf-8", errors="replace"))
        for t, kind in terms.items():
            if not t or t not in text:
                continue
            if kind != "deny list" and LONE_WORD.fullmatch(t.removesuffix(".md")):
                exempt.add((t, "one plain word"))
            elif kind != "deny list" and t in PUBLIC:
                exempt.add((t, PUBLIC[t]))
            elif kind != "deny list" and t in already_public:
                exempt.add((t, "already public in README on origin/main"))
            else:
                hits.append((f, kind, t))
        for i in range(len(text) - WINDOW + 1):
            run = text[i:i + WINDOW]
            if run in windows:
                if run in already_public:
                    exempt.add((run, "already public in README on origin/main"))
                else:
                    hits.append((f, "40-character run of note text", run))
                    break
    for t, why in sorted(exempt):
        print(f"  not counted: {t!r} ({why})")
    if hits:
        print(f"FAIL: {len(hits)} private match(es)")
        for f, kind, t in hits:
            print(f"  {f.relative_to(HERE.parent)}: {kind}: {t!r}")
        sys.exit(1)
    print(f"OK: {len(files)} published files, {len(terms)} private terms and "
          f"{len(windows)} 40-character runs of note text, no match.")


if __name__ == "__main__":
    main()
