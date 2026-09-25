# Filing tests: Jev on a real notes vault

Three pre-registered tests, run 23 and 24 September 2026, of one job: given a note from my own
second-brain vault, which of eight folders does it belong in? Jev (`jev-1.13.0`) against Claude
Sonnet 5 (`anthropic/claude-sonnet-5` via OpenRouter), five runs of each model arm and one of
the deterministic retrieval arm. The folder a note
was filed in is its label. They are the numbers behind the write-up [Jev, a cheap AI, did two
thirds of my filing: same result as Claude, 63% cheaper](https://jamiewatters.work/journey/jev-files-my-notes).

The notes are private, so what is published here is every model answer, every figure and every
script, with no note text. Anyone can recompute the figures in the three verdicts from the
answers:

```bash
python3 filing/reproduce.py      # no keys, no network, standard library; exits 0 if all match
```

## The three results

| Test | Question | Result (majority answer of five runs) |
|---|---|---|
| 1, 83 notes | Jev against Claude, the note alone | Jev 65.1%, Claude 77.1%, p = 0.013. Jev loses. |
| 1b, same 83 | Add ten retrieved, already-filed notes as examples | Jev 83.1%, the retrieval alone 74.7% (p = 0.189), Claude with the same examples 89.2% (p = 0.0625). "The retrieval did the work." |
| 1c, 75 fresh notes | Jev keeps its 80%-sure answers and passes the rest to Claude | 86.7%, the same 65 of 75 notes as Claude alone, at $0.00340 a note against $0.00909: 37% of Claude's cost. Jev passed 32.5% on. "Escalation pays." |

Neither model, alone or together, meets the pre-registered bar for acting unsupervised (at most
5% of confident answers wrong). The verdicts say what that means and what the tests cannot show.

## What is here

```
reproduce.py        runs the scoring scripts on the published data, checks every verdict figure
check_public.py     the leak check (needs the private files; see below)
preregistrations/   the three pre-registrations, as approved (one note path redacted in 1b)
verdicts/           the three verdicts, notes referred to by id only
code/               every script that built the keys, made the calls and scored them
runs/               all 47 run files, one row per note per call, reduced (below)
summaries/          the scored outputs, as the private scoring wrote them
data/               the reduced keys and neighbour lists, the question wording, frozen hashes
```

Notes are `r-001` to `r-083` (the Test 1 and 1b set) and `h-001` to `h-075` (the Test 1c
held-out set). The eight folders are mission-control, income-bridge, books, efformism, content,
knowledge, reference and delete.

## How the redaction works

Private and never published: note text, titles, paths, filenames, the examples each model was
shown, the neighbour lists as notes, the pool of 605 notes they were drawn from, and any
sentence that says what a note is.

- **Runs** keep, per row: note id, the folder it was filed in (`label`), the answer
  (`predicted`), confidence, the keep flag, Jev's probabilities or yes/no values, the retrieval
  arm's vote count per folder, tokens, cost, the model asked and the model that answered, and the
  run label. Dropped: Claude's raw reply (it only repeats the answer and confidence) and the
  seconds per call. Filenames and row order are unchanged.
- **Keys** (`data/routing-key.jsonl`, `data/test1c-heldout.jsonl`) keep id and folder only
  (the first also has `title` and `path` fields reading `[withheld]`, because `describe.py`
  expects them).
- **Neighbour lists** (`data/test1b-neighbours.jsonl`, `data/test1c-neighbours.jsonl`) keep,
  for each of a note's ten examples, only its rank, its folder, whether it is a near-duplicate
  and, if the example is itself a test note, that note's id. No path, title, text or score.
- **Summaries** are byte-identical to the private ones, except that in
  `routing-descriptive.json` each confident error's title and path read `[withheld]`.
- **Verdicts** are the private verdicts with every description of a note removed and marked;
  every number is unchanged.
- **Code** is as run, with three passages marked as redacted for publication: the personal
  profile used only by the ideas task, which never ran, and the comment naming its source file;
  and a docstring saying what two near-duplicate notes were. None changes a result.
- **Question wording** (`data/test1c-*.json`): the instructions and folder descriptions Jev was
  given are exactly as run. In the change log, a quotation that names private folders is
  withheld, and in the round-2 files an internal project code.

`reproduce.py` runs the scoring scripts in `code/` unchanged. Two things in them read private
files: the Test 1b neighbour list and pool (for the near-duplicate ids, the pool size and the
hashes) and the Test 1c neighbour list. Those reads are pointed at the reduced files. The four
regenerated summaries must match `summaries/` byte for byte, which fixes every percentage,
p-value, interval, id list and confusion table the verdicts quote from them. Then 42 checks
recompute the figures the verdicts quote that are not a field in a summary (counts by folder,
note ids, cost ratios, spend) and compare each with the value written in the verdict.

Its limits: the expected values are typed into `reproduce.py`, not read from the verdict text,
so compare the two yourself; the pool size, the per-folder pool counts and the hashes come from
`data/frozen-facts.json` and cannot be recomputed without the pool; and matching summaries prove
the scripts turn these runs into these numbers, not that the runs are the originals.

## What cannot be checked from here

- **The labels and the calls.** Without the notes you cannot see whether a label is right or
  re-ask a model. You can check that every figure follows from the answers recorded.
- **The frozen files.** The pool, the keys, the neighbour lists and the question files were
  hashed before the calls. The files cannot be published; their sha256 values are in
  `data/frozen-facts.json`, so the private originals can be shown unchanged later. The published
  question files do not match their hashes, because of the withheld passages in their change log.

## The leak check

`check_public.py` exits 0 only if no file under `filing/`, nor the repository README,
contains any path, filename, title or 40-character run of text from the private key, held-out
and pool files. It needs those files, so only their holder can run it:

```bash
python3 filing/check_public.py --private-dir <folder holding the private data files>
```

It prints the few things it does not count as a leak, with the reason: one plain word that is
also a note's title (`summary`, a folder name), terms already public in this README, and the
title of the author's published book, which the routing prompt names.
