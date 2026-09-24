#!/usr/bin/env python3
"""Build the two answer keys for Test 1 (T-809): inbox routing and the ideas queue.

    python3 build_keys.py routing     # writes data/routing-key.jsonl
    python3 build_keys.py ideas       # writes data/ideas-items.jsonl (labels added later)

Routing: the label is the home a note ended up in. The first plan was to use only notes
that passed through 0-Inbox, but the vault's git ignores the inbox, so there is no record
of moves, and the notes that carry a capture stamp (93 of them on 23 Sep) are nearly all
in knowledge/. A key where one answer is right 90% of the time measures the majority
class, not routing. So the key is a stratified sample: up to PER_HOME notes from each
home, drawn with a fixed seed, so the draw can be re-made and checked.

The item a model sees is the note's title and the start of its body, with the
frontmatter removed, because frontmatter such as `type: book-note` is written at filing
time and gives the answer away. Nothing else is removed.
"""

import json
import pathlib
import random
import re
import sys
import datetime as dt

HERE = pathlib.Path(__file__).resolve().parent
VAULT = HERE.parent.parent
DATA = HERE / "data"
SEED = 809
PER_HOME = 15
BODY_CHARS = 1500

# label -> the folders whose notes carry that label
HOMES = {
    "mission-control": ["mission-control/projects", "mission-control/products"],
    "income-bridge": ["income-bridge"],
    "books": ["books"],
    "efformism": ["efformism"],
    "content": ["content/ideas", "content/published", "content/drafts"],
    "knowledge": ["knowledge"],
    "reference": ["reference"],
}

# knowledge/readwise is synced straight in by a plugin and never passes through filing.
EXCLUDE_PARTS = {"readwise", "node_modules", "artboards"}

# content/drafts holds each article's by-products beside it (hooks, reviews, socials).
# They are pipeline scratch, not notes anyone routes, so only the article itself counts.
DRAFT_BYPRODUCT = re.compile(
    r"-(hooks|titles|images|figures|linkedin|twitter|x|wip|reviews?(-r\d+)?|review-"
    r"(prompt|assessment)|internal-review|socials?|thread)$")


def eligible(label, path):
    rel = path.relative_to(VAULT)
    if any(p.startswith((".", "_")) or p in EXCLUDE_PARTS for p in rel.parts):
        return False
    if label == "content" and rel.parts[1] == "drafts":
        if len(rel.parts) != 3 or DRAFT_BYPRODUCT.search(path.stem):
            return False
    return True


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def item_text(path):
    body = strip_frontmatter(path.read_text(encoding="utf-8", errors="replace")).strip()
    m = re.search(r"^#\s+(.+)$", body, re.M)
    title = m.group(1).strip() if m else path.stem
    return title, body[:BODY_CHARS]


def file_date(path):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    if m:
        return m.group(1), "filename"
    return dt.date.fromtimestamp(path.stat().st_mtime).isoformat(), "mtime"


def build_routing():
    rng = random.Random(SEED)
    rows, pool_sizes = [], {}
    for label, folders in HOMES.items():
        pool = sorted({p for f in folders for p in (VAULT / f).rglob("*.md")
                       if eligible(label, p)})
        pool_sizes[label] = len(pool)
        pick = pool if len(pool) <= PER_HOME else rng.sample(pool, PER_HOME)
        for p in sorted(pick):
            title, text = item_text(p)
            date, date_src = file_date(p)
            rows.append({
                "id": f"r-{len(rows) + 1:03d}",
                "label": label,
                "path": str(p.relative_to(VAULT)),
                "date": date,
                "date_source": date_src,
                "title": title,
                "text": text,
            })
    DATA.mkdir(exist_ok=True)
    out = DATA / "routing-key.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    dates = sorted(r["date"] for r in rows)
    summary = {
        "items": len(rows),
        "seed": SEED,
        "per_home_cap": PER_HOME,
        "pool_sizes": pool_sizes,
        "per_label": {k: sum(1 for r in rows if r["label"] == k) for k in HOMES},
        "date_range": [dates[0], dates[-1]],
        "dated_by_filename": sum(1 for r in rows if r["date_source"] == "filename"),
        "built": dt.datetime.now().isoformat(timespec="seconds"),
    }
    (DATA / "routing-key-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def build_ideas():
    """The open rows of 17-CANDIDATES.md, as stored. Labels are Jamie's, added after."""
    table = (VAULT / "mission-control" / "17-CANDIDATES.md").read_text(encoding="utf-8")
    rows = []
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 8 or not re.fullmatch(r"C-\d+", cells[0]):
            continue
        cid, proposed, source, tag, proposal, served, skips, status = cells
        if "open" not in status:
            continue
        rows.append({"id": cid, "proposed": proposed, "source": source, "tag": tag,
                     "proposal": proposal})
    DATA.mkdir(exist_ok=True)
    out = DATA / "ideas-items.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} open ideas-queue rows -> {out.relative_to(HERE)}")


if __name__ == "__main__":
    {"routing": build_routing, "ideas": build_ideas}[sys.argv[1]]()
