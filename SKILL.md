---
name: ds-python-interview
description: Practice and drill Python data-science interview questions in Jupyter notebooks with spaced repetition. A stdlib-only CLI handles the bookkeeping (question bank, notebook generation, scheduling); Claude does the reasoning (writing questions, parsing screenshots, reviewing completed notebooks). Use when the user wants to practice/drill Python DS interview questions, generate a practice notebook, review a completed notebook, add an interview question from text or a screenshot, expand a leaked/partial question into a full easy-to-hard set, check what's due to review, or see their progress/stats. Covers three categories — pure-Python DSA, pandas/numpy data manipulation, and statistics/experimentation (CUPED, delta method, IPTW, bootstrap, power/MDE). ML-from-scratch is intentionally out of scope.
---

# DS Python Interview Trainer

## Overview

This skill helps you practice Python data-science interview questions using
Jupyter notebooks and spaced repetition. It is a thin division of labor:

- **A companion CLI** (`scripts/ds_python_interview_cli.py`, standard library
  only) does all the **bookkeeping** — storing questions, building notebooks,
  tracking what's due, and updating the spaced-repetition schedule.
- **Claude** does all the **reasoning** — generating new grounded questions,
  parsing pasted text or screenshots, writing model solutions, and reviewing
  your completed notebooks against an answer key.

Questions span three categories — `dsa` (pure Python / stdlib), `pandas` (data
manipulation), and `stats` (estimators and experimentation methods). ML
implemented from scratch is intentionally **out of scope**.

## When to Use

Trigger this skill when the user wants to:

- Practice / drill Python DS interview questions or **generate a practice notebook**.
- **Review a completed notebook** ("review my notebook", "grade my answers").
- **Add a question** from pasted text or a **screenshot** image.
- **Expand a leaked / partial question** into a full easy → hard progression.
- See **what's due** for review, or view **stats / progress**.

## Prerequisites

- **Python 3.10+** to run the CLI. The CLI is **standard library only** — no
  third-party packages are needed for bookkeeping or notebook building.
- To *solve* notebooks, the user needs **Jupyter / JupyterLab** or **VS Code**
  (with the Jupyter extension).
- **pandas / numpy / scipy / statsmodels** are only needed *at solve time*
  inside the notebook kernel — the skill and CLI never import them. The user
  installs whatever the questions they practice require.

## How It Works

The CLI owns a single output directory (the **bank dir**). Everything is stored
there as plain files: markdown notes for each question, generated notebooks, and
a JSON index that doubles as the spaced-repetition state. Claude reads and
writes those files through the CLI (and the Read tool) and never has to
hand-track schedules or IDs.

- Default bank dir: `./interview_bank`
- Override per-command with `--bank-dir PATH`, or set the env var
  `DS_PY_INTERVIEW_BANK_DIR`.
- **Every** command accepts `--bank-dir`.

Question generation is **grounded** in `references/question_taxonomy.md` so that
new questions match real interview surface area and difficulty. Reviews are
graded against `references/grading_rubric.md`. Scheduling follows
`references/spaced_repetition.md`, which mirrors the CLI's algorithm exactly.

### CLI commands

```bash
# Add one or more questions from a JSON file (object or array).
# Keys: category, difficulty, title, prompt, examples, constraints,
#       tags, source, solution, complexity, staff_signals
python3 scripts/ds_python_interview_cli.py add --from-json ./new_questions.json
# (single-question direct flags are also supported; use --update to overwrite)

# Build the WORKING + KEY notebooks for a session (due questions first, then fresh).
python3 scripts/ds_python_interview_cli.py generate-notebook \
    --category pandas --difficulty medium --num 5

# List questions due for review (optionally filtered).
python3 scripts/ds_python_interview_cli.py due --category dsa --limit 10

# Browse the bank.
python3 scripts/ds_python_interview_cli.py list --tag groupby

# Extract each question's answer code from a (completed) notebook as JSON.
python3 scripts/ds_python_interview_cli.py parse-notebook \
    --notebook ./interview_bank/Notebooks/drill_2026-01-15.ipynb

# Record a review outcome and update the schedule.
python3 scripts/ds_python_interview_cli.py grade \
    --id q_pandas_rolling-retention --grade good --notes "clean, used transform"

# Progress summary.
python3 scripts/ds_python_interview_cli.py stats
```

Notes:
- `add` writes a Bank note (`Bank/q_<category>_<slug>.md`) and registers
  spaced-repetition state. `--update` overwrites an existing question.
- `generate-notebook` takes `--num N` and optional `--ids ...` and
  `--date YYYY-MM-DD`. It pulls **due questions first, then fresh ones** to
  reach `N`.
- `due` and `grade` accept `--as-of YYYY-MM-DD` to evaluate the schedule for a
  specific date.

## The Five Workflows

### 1. Generate a notebook

The user picks a `category` and `difficulty` for the session. First make sure
enough **grounded** questions exist: pull due ones and, if needed, generate new
questions (grounded in `references/question_taxonomy.md`), write model
solutions, and `add` them. Then build the notebooks.

```bash
python3 scripts/ds_python_interview_cli.py generate-notebook \
    --category stats --difficulty hard --num 4
```

This emits a **working** notebook with sequential questions **Q1 → QN**
(each prompt followed by an empty answer cell) and a separate **`_KEY`**
notebook containing model solutions plus complexity / staff-signal notes:

```
./interview_bank/Notebooks/drill_2026-01-15.ipynb       # working (no solutions)
./interview_bank/Notebooks/drill_2026-01-15_KEY.ipynb   # answer key
```

Tell the user the path and how to open it, e.g. `jupyter lab`, open it in
**VS Code**, or run `jupyter notebook <path>`.

### 2. Solve (done by the user, outside the skill)

The user opens the **working** notebook and fills in the empty code cell under
each question, working **Q1 → QN**, then saves the file. (They should *not*
open the `_KEY` notebook until they're done.)

### 3. Review a completed notebook

When the user says **"review my notebook"**, read the completed working
notebook (via the Read tool, or `parse-notebook` for a deterministic
question → answer-code mapping). Evaluate each answer against the `_KEY` using
`references/grading_rubric.md`. Optionally execute cells to verify correctness.
Write a per-question report to `Reviews/review_<date>.md`, then call `grade`
once per question to advance its schedule.

```bash
python3 scripts/ds_python_interview_cli.py parse-notebook \
    --notebook ./interview_bank/Notebooks/drill_2026-01-15.ipynb
# ...evaluate, write Reviews/review_2026-01-15.md, then per question:
python3 scripts/ds_python_interview_cli.py grade \
    --id q_dsa_sliding-window-max --grade hard --notes "correct but O(n log n)"
```

### 4. Ingest a question (text or screenshot)

The user pastes a question as **text** or a **screenshot image**. Parse out the
prompt, examples, and constraints; classify `category`, `difficulty`, and
`tags`; write a clean **model solution** (with complexity and staff-level
signals); then `add` it so it flows into future notebooks.

```bash
python3 scripts/ds_python_interview_cli.py add --from-json ./ingested.json
```

### 5. Expand a leaked fragment

When the user shares a **partial / incomplete** leaked interview question:

1. **State what's being probed** — briefly infer the core skill/concept and the
   likely follow-ups the interviewer is steering toward.
2. **Reconstruct a full progression** of 3–6 step-by-step questions that ramp
   easy → hard: warm-up → core → edge cases / optimization → stretch.
3. **`add` each** question, then emit them as **one sequential notebook** via
   `generate-notebook --ids ...` so they appear as Q1 → QN in order.

```bash
python3 scripts/ds_python_interview_cli.py add --from-json ./expanded_set.json
python3 scripts/ds_python_interview_cli.py generate-notebook \
    --category pandas --difficulty medium --num 5 \
    --ids q_pandas_warmup q_pandas_core q_pandas_edges q_pandas_stretch
```

## Output Format

Everything lives under the bank dir (default `./interview_bank`):

```
interview_bank/
  Bank/         # one markdown note per question: q_<category>_<slug>.md
  Notebooks/    # drill_<YYYY-MM-DD>.ipynb (working) + drill_<YYYY-MM-DD>_KEY.ipynb (key)
  Reviews/      # review_<YYYY-MM-DD>.md  (Claude writes per-question feedback)
  _index.json   # canonical question store + spaced-repetition state
```

- **Working notebook** — intro cell, then for each question a markdown prompt
  (`## Q{n} — Title`, examples, constraints, tags) followed by an empty answer
  cell. No solutions.
- **KEY notebook** — same prompts, but each answer cell holds the model
  solution, followed by a notes cell with **complexity** and **staff signals**.
- **Review report** — `Reviews/review_<date>.md`, one section per question:
  the grade across each rubric dimension, what was right/wrong, the fix, and the
  spaced-repetition grade assigned.

## Resources

- `references/question_taxonomy.md` — what to generate: the three categories,
  difficulty rubric, the library/skill surface each should exercise, and example
  questions. **Ground all generated questions in this file.**
- `references/grading_rubric.md` — how to evaluate a submitted answer and map
  the result to a spaced-repetition grade.
- `references/spaced_repetition.md` — the exact SM-2-lite schedule the CLI
  implements, and how `due` drives the next notebook.

## Key Principles

- **CLI bookkeeps, Claude reasons.** Never hand-track IDs, schedules, or file
  paths — go through the CLI. Never invent question content the CLI should
  store; `add` it.
- **Ground every generated question** in `references/question_taxonomy.md` so
  difficulty and surface area stay realistic.
- **Always produce a separate KEY** so review is grounded in a reference answer.
- **Grade honestly.** Map review outcomes to `{again, hard, good, easy}` per
  `references/grading_rubric.md`; an honest grade is what makes spaced
  repetition work.
- **ML-from-scratch is out of scope** — keep questions within `dsa`, `pandas`,
  and `stats`.
- **Default to `./interview_bank`**; respect `--bank-dir` /
  `DS_PY_INTERVIEW_BANK_DIR` when provided.
