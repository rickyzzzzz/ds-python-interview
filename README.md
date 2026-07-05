# ds-python-interview

A [Claude Code](https://claude.com/claude-code) skill for practicing **Python
data-science interview questions** in Jupyter notebooks, with built-in **spaced
repetition**.

It splits the work cleanly:

- **A standard-library-only CLI** does the bookkeeping — storing questions,
  generating notebooks, tracking what's due, and updating the spaced-repetition
  schedule.
- **Claude** does the reasoning — writing grounded questions, parsing pasted
  text or screenshots, producing model solutions, and reviewing your completed
  notebooks against an answer key.

Questions span four categories:

- **`dsa`** — pure-Python / standard library (collections, itertools, heapq,
  sliding window, two pointers, DP, clean idiomatic code).
- **`pandas`** — data manipulation (groupby/transform/merge/reshape, window
  functions, vectorization; numpy broadcasting; scipy.stats).
- **`stats`** — implement an estimator or test (CUPED, delta method, IPTW,
  bootstrap, power/MDE) from scratch or with statsmodels/scipy.
- **`sql`** — analytics SQL answered as real queries inside the notebook: the
  setup cell loads small DataFrames into **in-memory SQLite** and defines a
  `q()` helper, so joins, window functions, and retention/NDR-style metrics
  run with zero extra dependencies. Supports **multi-step interview cases**
  (one business scenario ramped easy → hard across Q1→QN, with a planted data
  trap) — ideal for giving or receiving a mock SQL interview.

> ML-implemented-from-scratch is intentionally out of scope.

## What it does

1. **Generate a notebook** — pick a category + difficulty; get a working
   notebook with sequential questions **Q1 → QN**. Each question shows the
   **input data** and **expected output**, ships a **runnable setup cell** that
   builds the dataset (so you can run cells and experiment), and gives you an
   empty answer cell. A separate `_KEY` notebook holds the model solutions.
2. **Solve** — work through the questions in JupyterLab / VS Code.
3. **Review** — Claude reads your completed notebook, grades each answer against
   the key, writes a feedback report, and updates the schedule.
4. **Ingest** — paste a question as text or a screenshot; Claude parses it,
   writes a model solution, and banks it.
5. **Expand a leaked fragment** — share a partial/leaked question; Claude infers
   what's being probed and reconstructs a full easy → hard set.
6. **Add follow-ups** — after solving, ask for deeper variants; Claude asks what
   kind you want (scale, edge cases, SQL, harder, stats, Python internals) and
   appends new questions onto your existing notebook (Q4, Q5, …).
7. **Build a multi-step SQL mock case** — ask for a SQL interview case and get
   one scenario ramped over 2–4 escalating questions with a shared dataset, a
   working notebook for the interviewee, and a `_KEY` whose staff-signal notes
   double as the interviewer's probe list.

## Install

Clone (or copy) this folder into your Claude Code skills directory:

```bash
git clone https://github.com/rickyzzzzz/ds-python-interview.git \
  ~/.claude/skills/ds-python-interview
```

Claude Code discovers the skill automatically from its `SKILL.md`. Then just
ask Claude to "generate a medium pandas interview notebook", "review my
notebook", etc.

## Requirements

- **Python 3.10+** to run the CLI (standard library only — no install needed).
- **Jupyter / JupyterLab** or **VS Code** to *solve* the notebooks.
- `pandas` / `numpy` / `scipy` / `statsmodels` only at *solve time*, inside the
  notebook kernel, for whatever questions you practice. The skill itself never
  imports them.

## Quickstart (CLI)

The CLI writes everything under a single **bank dir** (default
`./interview_bank`; override with `--bank-dir` or the `DS_PY_INTERVIEW_BANK_DIR`
env var).

```bash
cd ~/.claude/skills/ds-python-interview

# Add questions from a JSON file (object or array)
python3 scripts/ds_python_interview_cli.py add --from-json ./questions.json

# Build a session's working + KEY notebooks (due first, then fresh)
python3 scripts/ds_python_interview_cli.py generate-notebook \
    --category pandas --difficulty medium --num 5

# See what's due, browse the bank, check progress
python3 scripts/ds_python_interview_cli.py due
python3 scripts/ds_python_interview_cli.py list --tag groupby
python3 scripts/ds_python_interview_cli.py stats

# After solving, record an outcome (updates spaced repetition)
python3 scripts/ds_python_interview_cli.py grade \
    --id q_pandas_rolling-retention --grade good
```

## Output layout

```
interview_bank/
  Bank/         # one markdown note per question: q_<category>_<slug>.md
  Notebooks/    # drill_<YYYY-MM-DD>.ipynb (working) + ..._KEY.ipynb (answer key)
  Reviews/      # review_<YYYY-MM-DD>.md  (per-question feedback)
  _index.json   # canonical question store + spaced-repetition state
```

## Layout of this repo

```
ds-python-interview/
  SKILL.md                         # skill definition Claude Code reads
  scripts/
    ds_python_interview_cli.py     # CLI entry point (stdlib only)
    notebook_builder.py            # build/parse nbformat v4 notebooks
    tests/test_cli.py              # unit tests
  references/
    question_taxonomy.md           # what to generate (grounds question writing)
    grading_rubric.md              # how to evaluate an answer
    spaced_repetition.md           # the SM-2-lite schedule the CLI implements
```

## Tests

```bash
python3 scripts/tests/test_cli.py -v
```

## License

MIT — see [LICENSE](LICENSE).
