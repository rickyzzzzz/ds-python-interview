# Question Taxonomy

Ground every generated question in this guide so difficulty and surface area
match what data-science interviews actually test. There are four categories,
each scored on a three-level difficulty rubric. ML implemented from scratch is
**out of scope**.

---

## Categories

### `dsa` — pure Python / standard library

Idiomatic, efficient Python with no third-party packages. The point is data
structures, algorithmic thinking, and clean code under time pressure.

**Surface area to exercise:**

- `collections` — `Counter`, `defaultdict`, `deque`, `OrderedDict`.
- `itertools` — `groupby`, `accumulate`, `product`, `combinations`, `chain`,
  `islice`, `pairwise`.
- `functools` — `lru_cache`, `reduce`, `cmp_to_key`.
- `heapq` — top-k, merge of sorted streams, running median.
- `bisect` — insertion points, searching sorted arrays.
- Patterns: **sliding window**, **two pointers**, prefix sums, hashing,
  interval merging, **dynamic programming** (1-D and 2-D), BFS/DFS on small
  graphs, string parsing.
- Clean idiomatic code: comprehensions, generators, unpacking, type hints.

### `pandas` — data manipulation

Realistic tabular wrangling: the kind of "here's a DataFrame, compute X" task a
DS sees daily. Vectorization is expected; Python row loops are a red flag.

**Surface area to exercise:**

- `groupby` + `agg` / `transform` / `apply`; named aggregations.
- `merge`, `merge_asof`, `join`; `concat`; many-to-one vs many-to-many.
- Reshape: `pivot`, `pivot_table`, `melt`, `stack` / `unstack`, `crosstab`.
- Window ops: `rolling`, `expanding`, `ewm`, `shift`, `diff`, `cumsum`,
  `rank`, `pct_change`.
- Time series: resampling, `groupby(pd.Grouper(...))`, asof joins, gap filling.
- Vectorization & **numpy broadcasting**; `np.where`, `np.select`, masking,
  `pd.cut` / `qcut`.
- Correct **NaN handling**, dtypes, `MultiIndex`, `value_counts`,
  `drop_duplicates`, `nlargest`.
- Occasional `scipy`/`numpy` for a numeric step (e.g. correlation, percentiles).

### `stats` — estimators & experimentation

Implement an estimator or test, either **from scratch** (numpy/scipy) or via
`statsmodels` / `scipy.stats`. This is the A/B-testing and causal-inference
surface, not ML modeling.

**Surface area to exercise:**

- Hypothesis tests via `scipy.stats`: t-test, Mann-Whitney, chi-square,
  proportions z-test, Kolmogorov-Smirnov.
- `statsmodels`: OLS / logit, robust / clustered standard errors, ANOVA.
- Experimentation: **power / MDE** calculation, sample-size, sequential-testing
  caveats, multiple-comparison correction.
- Variance reduction: **CUPED** (pre-period covariate adjustment).
- **Delta method** for ratio-metric variance.
- Causal weighting: **IPTW** (inverse propensity weighting), propensity scores.
- Resampling: **bootstrap** confidence intervals, permutation tests.
- Clean, correct math; state assumptions; vectorize the simulation.

### `sql` — analytics SQL (runs inside the notebook)

Real analytics-round SQL, answered as queries against an **in-memory SQLite
database built in the setup cell** — no server, no new dependencies. The setup
loads small DataFrames via `to_sql` and defines a `q()` helper so the answer is
pure SQL but the result renders as a DataFrame:

```python
conn = sqlite3.connect(":memory:")
accounts.to_sql("accounts", conn, index=False)
events.to_sql("events", conn, index=False)

def q(sql: str) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    return pd.read_sql_query(sql, conn)
```

SQLite supports window functions and CTEs (3.25+, 2018), so the full analytics
surface is drillable. Tell the interviewee the dialect and name the equivalents
where they differ (`strftime('%Y-%m', ...)` ~ `DATE_TRUNC('month', ...)`).

**Surface area to exercise:**

- Joins: inner vs left semantics, `USING`, fan-out on many-to-many keys,
  anti-joins (`NOT EXISTS` / `LEFT JOIN ... IS NULL`).
- Aggregation: `GROUP BY`, `HAVING`, `COUNT(DISTINCT ...)`, conditional
  aggregation (`SUM(CASE WHEN ...)`) as a pivot.
- Window functions: `ROW_NUMBER` / `RANK` / `DENSE_RANK` (tie semantics!),
  `LAG` / `LEAD`, running totals, share-of-total via `SUM(...) OVER (PARTITION BY ...)`.
- CTEs and layering: aggregate to the right grain first, then rank/compare;
  why a window result can't be filtered in the same `SELECT`'s `WHERE`.
- Dates: month bucketing, month-over-month comparisons, cohorting by first
  activity.
- Business metric patterns: **retention / churn / NDR**, funnels, top-N per
  group, DAU/WAU-style activity counts, ratio metrics with integer-division
  and divide-by-zero guards.
- The classic traps: naive self-joins that silently drop churned entities,
  ranking pre-aggregation rows, `COUNT(*)` vs `COUNT(DISTINCT)`, filtering the
  dimension after the join instead of before.

**Multi-step interview cases.** Real SQL rounds usually run one business
scenario through 2–4 escalating questions (warm-up aggregation → window
functions → a retention/funnel metric with a data trap). Generate these as
separate banked questions sharing the **same `setup`** (each question rebuilds
the database, so every question stays independently runnable), chained via
`parent` and titled `... (Step k/N)`, then emit them in order with
`generate-notebook --ids`. Theme the scenario on a realistic business (a
messaging app, a usage-billed API platform, a marketplace) and **plant a trap
in the data** — e.g. an entity that churns between periods so a naive inner
self-join overstates retention — and put the trap's wrong answer in the KEY's
staff signals.

---

## Difficulty Rubric

| | **easy** | **medium** | **hard** |
|---|---|---|---|
| `dsa` | one data structure or a single pass; obvious approach (`Counter`, a `set`, simple two-pointer) | non-trivial pattern: sliding window with shrink, 1-D DP, heap-based top-k, careful edge handling | 2-D DP, custom comparator + heap, multiple interacting structures, or a tight complexity target the naive solution misses |
| `pandas` | one `groupby`/`agg`, a filter, a simple merge or sort | `transform` vs `agg`, multi-key merge, reshape (pivot/melt), a window op, broadcasting | `merge_asof` / time-aligned joins, multi-step pipeline, correct NaN/tie semantics at scale, vectorizing something that "wants" a loop |
| `stats` | apply a single library test and read off the result; basic CI | implement an estimator (bootstrap CI, two-proportion power) with correct variance | CUPED, delta-method ratio variance, IPTW, or a full power/MDE simulation with assumptions stated and the math derived |
| `sql` | one join + `GROUP BY`, a `HAVING` filter, `COUNT(DISTINCT)` | window functions (top-N per group, `LAG` for period-over-period, share-of-total), correct grain + tie semantics, CTE layering | retention/churn/NDR or funnel metrics with a planted data trap (churned entities, new-cohort exclusion), conditional-aggregation pivots, divide-by-zero/integer-division guards |

A clean rule of thumb: **easy** = recall the right tool; **medium** = compose 2–3
operations correctly with the right edge handling; **hard** = hit a specific
complexity/variance target, derive the method, or handle non-obvious edge cases.

---

## Example Questions

Generic, no attribution. Use these as calibration, not as a fixed list.

### `dsa`

- **easy** — Given a list of integers, return the value that appears most often;
  break ties by smallest value. (Probes: `Counter`, tie-breaking.)
- **medium** — Given an array and window size `k`, return the maximum of every
  contiguous window in `O(n)`. (Probes: monotonic `deque` / sliding window;
  naive `O(nk)` is the trap.)
- **hard** — Given a list of `(start, end)` intervals, return the minimum number
  of rooms needed so no two overlapping intervals share a room. (Probes: sort +
  heap, or sweep line; careful boundary semantics.)

### `pandas`

- **easy** — Given an `events` DataFrame (`user_id`, `event`, `ts`), return the
  count of events per user, sorted descending. (Probes: `groupby.size`, sort.)
- **medium** — Given `orders` (`user_id`, `order_ts`, `amount`), add a column
  with each user's running average order amount **before** the current row.
  (Probes: `groupby.transform` / `expanding`, `shift` to exclude the current
  row.)
- **hard** — Given `impressions` and `clicks` (each with `user_id`, `ts`),
  attribute every click to the most recent prior impression within 30 minutes.
  (Probes: `merge_asof` with `direction='backward'` + `tolerance`, NaN handling
  for unattributed clicks.)

### `stats`

- **easy** — Given two arrays of conversion outcomes (0/1), run a two-proportion
  z-test and return the p-value and the lift. (Probes: `statsmodels`
  `proportions_ztest` or hand-rolled normal approximation.)
- **medium** — Estimate a 95% bootstrap confidence interval for the median of a
  sample using 10,000 resamples; vectorize the resampling. (Probes: numpy
  resampling, percentile CI, no Python loops.)
- **hard** — Given pre-period and experiment-period metrics per user, implement
  **CUPED** variance reduction and report the variance-reduced treatment effect
  and the percent variance reduced. (Probes: covariate adjustment, choosing
  theta, correct variance accounting.)

### `sql`

- **easy** — Given `accounts` (id, segment, channel) and `usage` (account_id,
  date, revenue), return monthly revenue and distinct active accounts per
  segment for one channel. (Probes: join + `WHERE` on the dimension, month
  bucketing, `COUNT(DISTINCT)` vs `COUNT(*)`.)
- **medium** — For one month, return each segment's top-2 accounts by revenue
  with their share of segment revenue. (Probes: aggregate to account grain
  *first*, `DENSE_RANK` vs `ROW_NUMBER` tie semantics, windowed `SUM` for
  share-of-total, filtering a window result requires a CTE/subquery.)
- **hard** — Compute month-over-month **net dollar retention** per segment:
  next-month revenue from accounts active in the base month / base-month
  revenue, excluding new accounts, with churned accounts still dragging the
  ratio down. (Probes: conditional-aggregation pivot vs the naive inner
  self-join that silently drops churned accounts, cohort discipline, `100.0`
  float multiplication, `NULLIF` guard.)

---

## How Interviewers Probe (round → skill)

| Round / setting | What it tests | Category lean |
|---|---|---|
| Phone screen / warm-up | recall the right tool fast, clean syntax | `dsa` easy, `pandas` easy |
| Coding round | algorithmic correctness + complexity target | `dsa` medium/hard |
| Analytics / data-manipulation round | wrangling realistic tables, vectorization | `pandas` medium/hard |
| SQL / analytics-engineering round | joins, window functions, metric definitions on a business scenario | `sql` easy → hard as a multi-step case |
| Experimentation / stats round | A/B design, variance, causal reasoning | `stats` medium/hard |
| Senior / staff bar (any round) | edge cases, assumptions stated, communicates trade-offs, would read well under time pressure | hard across all |

When generating a set, mirror this: open with a warm-up, build to the core
skill, then push into edge cases / optimization, and (for senior practice) a
stretch question that forces stating assumptions and trade-offs.

---

## Make Every Question Runnable

So the working notebook is self-contained and the interviewee can actually run
cells and play with the data, every generated question must include:

- **`setup`** — runnable Python that constructs the input data and displays it.
  Keep the dataset small and illustrative (a handful of rows), assume `pandas as
  pd` / `numpy as np` are imported (the notebook adds a shared imports cell), and
  end the cell with the input variable so running it previews the data, e.g.:

  ```python
  orders = pd.DataFrame({
      "customer_id": [1, 1, 2, 3, 3],
      "amount": [10.0, 30.0, 50.0, 5.0, 15.0],
  })
  orders
  ```

- **`input_preview`** — a short static rendering of the input (so the question
  reads clearly without running anything).
- **`expected`** — the expected output for that input, shown in the prompt.

For `dsa` questions the `setup` typically defines plain Python inputs (a list,
string, or dict); for `pandas` it builds the DataFrame(s); for `stats` it builds
the sample arrays / frames; for `sql` it builds the DataFrames, loads them into
an in-memory SQLite connection, and defines the `q()` helper (see the `sql`
category above) — so the answer cell is just `q("""SELECT ...""")`. The dataset
in `setup` should match `input_preview` and produce the `expected` output, so
the example is internally consistent. For `sql`, **verify the solution queries
against the setup data before banking** (run them via `sqlite3` + pandas) so
`expected` is exact, not hand-computed.

---

## Follow-up Kinds

After a question is solved, a follow-up deepens it along one axis. Ask the user
which axis they want, then generate a new question (with its own
`setup`/`input_preview`/`expected`/`solution`) seeded by the parent. The common
kinds — interviewers reuse almost all of these:

| Kind | The prompt twist | Probes |
|---|---|---|
| **Scale / performance** | "Now it's 100M rows and won't fit in memory." | chunking, dtypes/`category`, push to SQL/Spark, approximate algorithms |
| **Edge cases & robustness** | "Handle NaN / ties / empty / duplicate or unmatched keys." | deliberate missing-data and boundary handling, `validate=` on joins |
| **SQL translation** | "Write the same logic as a SQL query." | `GROUP BY`, `JOIN`, window functions, `COUNT(DISTINCT …)` |
| **Harder variant** | The next difficulty tier of the same skill. | `transform` vs `agg`, `merge_asof`, ratio metrics, top-k heap, 2-D DP |
| **Stats bridge** | "Is that difference significant? How would you size the test?" | hypothesis test choice + assumptions, power/MDE, CUPED, delta method |
| **Python internals** | "Why is this fast/slow? What does it copy?" | view vs copy, generators, hashing, complexity, GIL |

The general shape: a follow-up makes the original **faster, bigger, break, real
(SQL/prod), or rigorous (stats)**. Tag follow-ups with a `followup` tag and set
the question's `parent` to the source question's id so the lineage is queryable.
