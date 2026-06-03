# Question Taxonomy

Ground every generated question in this guide so difficulty and surface area
match what data-science interviews actually test. There are three categories,
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

---

## Difficulty Rubric

| | **easy** | **medium** | **hard** |
|---|---|---|---|
| `dsa` | one data structure or a single pass; obvious approach (`Counter`, a `set`, simple two-pointer) | non-trivial pattern: sliding window with shrink, 1-D DP, heap-based top-k, careful edge handling | 2-D DP, custom comparator + heap, multiple interacting structures, or a tight complexity target the naive solution misses |
| `pandas` | one `groupby`/`agg`, a filter, a simple merge or sort | `transform` vs `agg`, multi-key merge, reshape (pivot/melt), a window op, broadcasting | `merge_asof` / time-aligned joins, multi-step pipeline, correct NaN/tie semantics at scale, vectorizing something that "wants" a loop |
| `stats` | apply a single library test and read off the result; basic CI | implement an estimator (bootstrap CI, two-proportion power) with correct variance | CUPED, delta-method ratio variance, IPTW, or a full power/MDE simulation with assumptions stated and the math derived |

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

---

## How Interviewers Probe (round → skill)

| Round / setting | What it tests | Category lean |
|---|---|---|
| Phone screen / warm-up | recall the right tool fast, clean syntax | `dsa` easy, `pandas` easy |
| Coding round | algorithmic correctness + complexity target | `dsa` medium/hard |
| Analytics / data-manipulation round | wrangling realistic tables, vectorization | `pandas` medium/hard |
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
the sample arrays / frames. The dataset in `setup` should match `input_preview`
and produce the `expected` output, so the example is internally consistent.
