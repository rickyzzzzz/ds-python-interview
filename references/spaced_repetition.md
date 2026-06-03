# Spaced Repetition

The CLI schedules reviews with an **SM-2-lite** algorithm. This document
describes that algorithm **exactly** as the CLI implements it, so the docs and
the code never drift. When you call `grade`, this is what happens to the card.

---

## Card state

Each question (card) carries three numbers plus a date:

- `ease` — a multiplier controlling how fast intervals grow. **New default: 2.5.**
  Never allowed below **1.3** (the floor).
- `interval_days` — days until the next review. **New default: 0.**
- `reps` — count of *successful* reviews in the current streak. **New default: 0.**
- `next_review_date` — when the card becomes due.

A brand-new card added via `add` starts at `ease=2.5`, `interval_days=0`,
`reps=0`, and is immediately due.

---

## The four grades

`grade --grade {again, hard, good, easy}`. Plain-language meaning:

- **again** — failed; couldn't finish or got it wrong. Resets the streak.
- **hard** — got there, but it was a struggle (messy, hints, wrong complexity).
- **good** — solid pass; correct and clean. The normal "I knew this" grade.
- **easy** — effortless and optimal; push it far into the future.

---

## Update rules

Applied when a grade is recorded. `interval` below means `interval_days`.

### again
```
reps     = 0
interval = 1
ease     = max(1.3, ease - 0.20)
```

### hard
```
interval = max(1, round(interval * 1.2))
ease     = max(1.3, ease - 0.15)
reps     = reps + 1
```

### good
```
if reps == 0:   interval = 1
elif reps == 1: interval = 6
else:           interval = round(interval * ease)
reps = reps + 1
```

### easy
```
if reps == 0:   interval = 2
elif reps == 1: interval = 6
else:           interval = round(interval * ease * 1.3)
ease = ease + 0.15
reps = reps + 1
```

Then, for **every** grade:
```
next_review_date = today + interval_days
```
(where `today` is the `--as-of` date if provided, otherwise the current date).

Notes that fall out of these rules:

- `ease` only **decreases** on `again`/`hard` and only **increases** on `easy`;
  `good` leaves `ease` unchanged. The floor is **1.3**; there is no ceiling.
- `again` always sends the card to **tomorrow** (`interval = 1`) and wipes the
  streak (`reps = 0`).
- The first two successful `good` reviews use fixed intervals (**1**, then
  **6** days); only from the third does the interval scale by `ease`.
- `easy` ramps faster than `good` at every step and additionally widens future
  intervals by raising `ease`.

---

## How `due` drives the next notebook

`due` lists every card whose `next_review_date` is on or before the as-of date
(today by default, or `--as-of YYYY-MM-DD`). New cards (`interval_days = 0`) are
due immediately.

When building a session, `generate-notebook` fills the requested `--num N` by
taking **due questions first**, then topping up with **fresh** (never-reviewed)
questions in the chosen category/difficulty. So:

- Cards you graded **again** resurface the next day.
- Cards you graded **good**/**easy** drop out of rotation until their interval
  elapses, leaving room for new material.
- Over time the bank self-prioritizes the questions you keep getting wrong.

Check the queue any time:

```bash
python3 scripts/ds_python_interview_cli.py due --as-of 2026-01-20
python3 scripts/ds_python_interview_cli.py stats
```
