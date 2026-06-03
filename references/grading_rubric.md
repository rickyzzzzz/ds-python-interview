# Grading Rubric

Use this when reviewing a completed notebook. For each question, compare the
user's `answer_code` against the `_KEY` solution along five dimensions, write
the verdict to `Reviews/review_<date>.md`, then map the overall result to a
spaced-repetition grade and call `grade --id ... --grade ...`.

Where practical, **execute the answer cell** against the question's examples and
a few edge cases to verify correctness rather than eyeballing it.

---

## Dimensions

### 1. Correctness
Does the answer produce the right result on the stated examples **and** on edge
cases? This is the gate — if it's wrong on a valid input, nothing else saves it.

- [ ] Passes every stated example.
- [ ] Passes the edge cases listed below (Dimension 4).
- [ ] No crashes, no silent wrong answers (e.g. integer truncation, off-by-one).
- [ ] Result type/shape matches what was asked (Series vs DataFrame, scalar vs
      array, sorted vs unsorted).

### 2. Complexity
Did the solution hit the expected time/space bound from the KEY's complexity
note?

- [ ] Time complexity meets the target (e.g. `O(n)` sliding window, not `O(nk)`).
- [ ] Space is reasonable; no needless full copies of large structures.
- [ ] `pandas`: no hidden quadratic patterns (e.g. `.apply` calling a merge per
      row, repeated `concat` in a loop).
- [ ] `stats`: simulations/resampling are vectorized, not Python-looped.

### 3. Idiom / Vectorization
Is the code the way a strong candidate would write it?

- **pandas:** vectorized — `groupby` / `transform` / `merge` / broadcasting
  instead of `iterrows` or row-wise `apply`. Right tool for the job
  (`transform` vs `agg`, `merge_asof` vs manual loop).
- **dsa:** clean idiomatic Python with the right data structure (`Counter`,
  `deque`, `heapq`, `bisect`) rather than reinventing it; comprehensions and
  generators where they read better.
- **stats:** uses the appropriate library routine when one exists, or a correct,
  clearly-derived from-scratch implementation; states assumptions.

### 4. Edge cases
Did the answer handle the inputs that break naive solutions?

- [ ] Empty input / empty group.
- [ ] Single element.
- [ ] Ties (and the tie-break rule, if specified).
- [ ] Duplicates.
- [ ] `NaN` / missing data handling (pandas/stats) — dropped or propagated
      deliberately, not by accident.
- [ ] Boundary semantics (inclusive vs exclusive windows, off-by-one).

### 5. Communication / code quality (senior / staff bar)
Would this read well under interview time pressure?

- [ ] Clear names; no cryptic single letters for non-trivial values.
- [ ] Type hints / docstring where it adds clarity (esp. `dsa`).
- [ ] Small, readable steps; no dead code or debugging leftovers.
- [ ] States assumptions and trade-offs (esp. `stats`: which test, why; which
      variance estimator).
- [ ] Would a senior/staff interviewer nod at it, or ask for a rewrite?

---

## Mapping to a spaced-repetition grade

Pick the **single** grade that best describes the overall attempt, then call
`grade --id <question-id> --grade <grade>`. (See
`references/spaced_repetition.md` for what each grade does to the schedule.)

| Grade | When |
|---|---|
| **again** | Wrong on examples/edge cases, didn't finish, or fundamentally the wrong approach. The question needs to come back tomorrow. |
| **hard** | Correct in the end, but messy, sub-optimal complexity, needed hints, or missed obvious edge cases. Right idea, shaky execution. |
| **good** | Correct, clean, idiomatic/vectorized, hit the complexity target. Maybe a minor edge case or naming nit. The expected "passing" bar. |
| **easy** | Optimal complexity, all edge cases handled, fluent and idiomatic, assumptions/trade-offs stated. Nothing to add. |

Rules of thumb:

- **Any** correctness failure on a valid input → at best **again** (or **hard**
  only if it was a trivial, self-caught slip).
- Correct but **needed a hint** or has the wrong complexity → **hard**.
- Correct + clean + right complexity, minor nits only → **good**.
- Reserve **easy** for answers you'd let pass an actual senior/staff loop with
  no follow-up rewrite.

---

## Review report format

In `Reviews/review_<date>.md`, write one section per question:

```
## Q{n} — {title}   →   grade: good

- Correctness: PASS (verified on examples + empty/single)
- Complexity: O(n) as expected
- Idiom: vectorized with groupby.transform — good
- Edge cases: handled ties; did NOT handle empty group (minor)
- Communication: clear, but name `x` for the running total is vague

Fix: guard the empty-group case; rename `x` → `running_total`.
```

Then call `grade` for that question before moving to the next.
