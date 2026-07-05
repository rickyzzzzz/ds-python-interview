#!/usr/bin/env python3
"""CLI for a Python data-science interview practice skill.

Manages a bank of interview questions, generates Jupyter drill notebooks
(a WORKING copy and a KEY copy), parses completed notebooks, and tracks
spaced-repetition state with an SM-2-lite scheduler.

Standard library only. The on-disk state is a JSON index plus one markdown
note per question; all mutations use atomic writes.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

# Allow running either as a script or as a module by ensuring the script's
# directory is importable.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import notebook_builder  # noqa: E402

SCHEMA_VERSION = "1.0"
DEFAULT_BANK_DIRNAME = "./interview_bank"
ENV_BANK_DIR = "DS_PY_INTERVIEW_BANK_DIR"

CATEGORIES = {"dsa", "pandas", "stats", "sql"}
DIFFICULTIES = {"easy", "medium", "hard"}
GRADES = {"again", "hard", "good", "easy"}


# --------------------------------------------------------------------------- #
# Bank-dir resolution and small helpers
# --------------------------------------------------------------------------- #
def resolve_bank_dir(flag_value: str | None) -> Path:
    """Resolve the bank directory: flag > env var > built-in default."""
    if flag_value:
        return Path(flag_value).expanduser()
    env_value = os.environ.get(ENV_BANK_DIR)
    if env_value:
        return Path(env_value).expanduser()
    return Path(DEFAULT_BANK_DIRNAME)


def _bank_subdir(bank_dir: Path, name: str) -> Path:
    return bank_dir / name


def _index_path(bank_dir: Path) -> Path:
    return bank_dir / "_index.json"


def today_iso(value: str | None = None) -> str:
    if value:
        return value
    return _dt.date.today().isoformat()


def _parse_iso(value: str) -> _dt.date:
    return _dt.date.fromisoformat(value)


def slugify(text: str) -> str:
    """Return a kebab-case slug of the supplied text."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, str(path))
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def _normalize_tags(tags: Any) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return [str(t).strip() for t in tags if str(t).strip()]


# --------------------------------------------------------------------------- #
# Index load / save
# --------------------------------------------------------------------------- #
def load_index(bank_dir: Path) -> dict[str, Any]:
    path = _index_path(bank_dir)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("schema_version", SCHEMA_VERSION)
        data.setdefault("questions", {})
        return data
    return {"schema_version": SCHEMA_VERSION, "questions": {}}


def save_index(bank_dir: Path, index: dict[str, Any]) -> None:
    text = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(_index_path(bank_dir), text)


# --------------------------------------------------------------------------- #
# Spaced repetition (SM-2-lite)
# --------------------------------------------------------------------------- #
def new_sr_block(today: str) -> dict[str, Any]:
    return {
        "ease": 2.5,
        "interval_days": 0,
        "reps": 0,
        "last_reviewed": None,
        "next_review_date": today,
        "history": [],
    }


def apply_grade(sr: dict[str, Any], grade: str, today: str) -> dict[str, Any]:
    """Apply an SM-2-lite grade to a spaced-repetition block in place.

    ``today`` is an ISO date string. Returns the updated block.
    """
    ease = float(sr.get("ease", 2.5))
    interval = int(sr.get("interval_days", 0))
    reps = int(sr.get("reps", 0))

    if grade == "again":
        reps = 0
        interval = 1
        ease = max(1.3, ease - 0.20)
    elif grade == "hard":
        interval = max(1, round(interval * 1.2))
        ease = max(1.3, ease - 0.15)
        reps += 1
    elif grade == "good":
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        reps += 1
    elif grade == "easy":
        if reps == 0:
            interval = 2
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease * 1.3)
        ease = ease + 0.15
        reps += 1
    else:
        raise ValueError(f"Unknown grade: {grade}")

    today_date = _parse_iso(today)
    next_date = today_date + _dt.timedelta(days=interval)

    sr["ease"] = ease
    sr["interval_days"] = interval
    sr["reps"] = reps
    sr["last_reviewed"] = today
    sr["next_review_date"] = next_date.isoformat()
    sr.setdefault("history", []).append({"date": today, "grade": grade})
    return sr


# --------------------------------------------------------------------------- #
# Bank note rendering
# --------------------------------------------------------------------------- #
def render_bank_note(question: dict[str, Any]) -> str:
    """Render the markdown body (frontmatter + content) for a bank note."""
    tags = question.get("tags", [])
    fm_lines = ["---", f"id: {question['id']}", f"category: {question['category']}",
                f"difficulty: {question['difficulty']}"]
    fm_lines.append("tags: [" + ", ".join(tags) + "]")
    fm_lines.append(f"source: {question.get('source', '') or ''}")
    if question.get("parent"):
        fm_lines.append(f"parent: {question['parent']}")
    fm_lines.append(f"created: {question['created']}")
    fm_lines.append("---")

    body: list[str] = [""]
    body.append(f"# {question['title']}")
    body.append("")

    prompt = (question.get("prompt") or "").strip()
    if prompt:
        body.append("## Prompt")
        body.append("")
        body.append(prompt)
        body.append("")

    input_preview = (question.get("input_preview") or "").strip()
    if input_preview:
        body.append("## Input data")
        body.append("")
        body.append(input_preview)
        body.append("")

    expected = (question.get("expected") or "").strip()
    if expected:
        body.append("## Expected output")
        body.append("")
        body.append(expected)
        body.append("")

    setup = (question.get("setup") or "").strip()
    if setup:
        body.append("## Setup")
        body.append("")
        body.append("```python")
        body.extend(setup.splitlines())
        body.append("```")
        body.append("")

    examples = (question.get("examples") or "").strip()
    if examples:
        body.append("## Examples")
        body.append("")
        body.append(examples)
        body.append("")

    constraints = (question.get("constraints") or "").strip()
    if constraints:
        body.append("## Constraints")
        body.append("")
        body.append(constraints)
        body.append("")

    # Collapsible model solution as a Markdown callout block.
    solution = (question.get("solution") or "").strip()
    complexity = (question.get("complexity") or "").strip()
    staff_signals = (question.get("staff_signals") or "").strip()

    callout = ["> [!solution]- Model solution", "> ```python"]
    for line in solution.splitlines():
        callout.append(f"> {line}")
    callout.append("> ```")
    callout.append(f"> **Complexity:** {complexity}")
    callout.append(f"> **Staff signals:** {staff_signals}")
    body.extend(callout)
    body.append("")

    return "\n".join(fm_lines + body)


def read_bank_note(path: Path) -> dict[str, Any]:
    """Parse a bank note markdown file back into a question content dict.

    Recovers prompt/examples/constraints and the model solution (plus complexity
    and staff signals) from the rendered note so the full content is available
    for notebook generation without duplicating it in the index.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result: dict[str, Any] = {
        "prompt": "", "input_preview": "", "expected": "", "setup": "",
        "examples": "", "constraints": "",
        "solution": "", "complexity": "", "staff_signals": "",
    }

    # Split body sections by markdown headers (## ...), but stop section
    # collection when the solution callout begins.
    sections: dict[str, list[str]] = {}
    current: str | None = None
    solution_lines: list[str] = []
    in_solution = False
    in_code = False

    for line in lines:
        if line.startswith("> [!solution]"):
            in_solution = True
            continue
        if in_solution:
            stripped = line[2:] if line.startswith("> ") else line.lstrip(">")
            if stripped.strip() == "```python":
                in_code = True
                continue
            if stripped.strip() == "```":
                in_code = False
                continue
            if in_code:
                solution_lines.append(stripped)
            elif stripped.startswith("**Complexity:**"):
                result["complexity"] = stripped.split("**Complexity:**", 1)[1].strip()
            elif stripped.startswith("**Staff signals:**"):
                result["staff_signals"] = stripped.split("**Staff signals:**", 1)[1].strip()
            continue

        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    def _section_text(name: str) -> str:
        return "\n".join(sections.get(name, [])).strip()

    def _section_code(name: str) -> str:
        """Section text with surrounding ```python ... ``` fences stripped."""
        kept = [ln for ln in sections.get(name, []) if not ln.strip().startswith("```")]
        return "\n".join(kept).strip()

    result["prompt"] = _section_text("prompt")
    result["input_preview"] = _section_text("input data")
    result["expected"] = _section_text("expected output")
    result["setup"] = _section_code("setup")
    result["examples"] = _section_text("examples")
    result["constraints"] = _section_text("constraints")
    result["solution"] = "\n".join(solution_lines).strip()
    return result


# --------------------------------------------------------------------------- #
# Question construction
# --------------------------------------------------------------------------- #
def _build_question_record(raw: dict[str, Any], today: str) -> dict[str, Any]:
    category = (raw.get("category") or "").strip().lower()
    difficulty = (raw.get("difficulty") or "").strip().lower()
    title = (raw.get("title") or "").strip()

    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {sorted(CATEGORIES)}; got {category!r}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {sorted(DIFFICULTIES)}; got {difficulty!r}")
    if not title:
        raise ValueError("title is required")

    slug = slugify(title)
    qid = (raw.get("id") or f"q_{category}_{slug}").strip()
    tags = _normalize_tags(raw.get("tags"))

    return {
        "id": qid,
        "category": category,
        "difficulty": difficulty,
        "title": title,
        "tags": tags,
        "source": raw.get("source") or "",
        "parent": raw.get("parent") or "",
        "slug": slug,
        "created": today,
        "prompt": raw.get("prompt") or "",
        "input_preview": raw.get("input_preview") or "",
        "expected": raw.get("expected") or "",
        "setup": raw.get("setup") or "",
        "examples": raw.get("examples") or "",
        "constraints": raw.get("constraints") or "",
        "solution": raw.get("solution") or "",
        "complexity": raw.get("complexity") or "",
        "staff_signals": raw.get("staff_signals") or "",
    }


def _index_entry_from_record(record: dict[str, Any], note_path: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "category": record["category"],
        "difficulty": record["difficulty"],
        "title": record["title"],
        "tags": list(record["tags"]),
        "source": record["source"],
        "parent": record.get("parent", ""),
        "slug": record["slug"],
        "created": record["created"],
        "note_path": note_path,
        "sr": new_sr_block(record["created"]),
        "notebooks": [],
    }


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_add(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    today = today_iso(getattr(args, "date", None))

    raw_questions: list[dict[str, Any]]
    if args.from_json:
        with open(args.from_json, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        raw_questions = data if isinstance(data, list) else [data]
    else:
        if not (args.category and args.difficulty and args.title and args.solution):
            print("error: provide --from-json or --category/--difficulty/--title/--solution",
                  file=sys.stderr)
            return 2
        raw_questions = [{
            "category": args.category,
            "difficulty": args.difficulty,
            "title": args.title,
            "prompt": args.prompt,
            "input_preview": args.input_preview,
            "expected": args.expected,
            "setup": args.setup,
            "examples": args.examples,
            "constraints": args.constraints,
            "tags": args.tags,
            "source": args.source,
            "parent": args.parent,
            "solution": args.solution,
            "complexity": args.complexity,
            "staff_signals": args.staff_signals,
        }]

    index = load_index(bank_dir)
    bank_subdir = _bank_subdir(bank_dir, "Bank")
    added_ids: list[str] = []

    for raw in raw_questions:
        record = _build_question_record(raw, today)
        qid = record["id"]
        if qid in index["questions"] and not args.update:
            print(f"error: question id {qid!r} already exists (use --update to overwrite)",
                  file=sys.stderr)
            return 1

        note_filename = f"q_{record['category']}_{record['slug']}.md"
        note_path = bank_subdir / note_filename
        _atomic_write_text(note_path, render_bank_note(record))
        rel_note_path = os.path.relpath(note_path, bank_dir)

        if qid in index["questions"] and args.update:
            # Preserve SR history and notebooks on update.
            existing = index["questions"][qid]
            entry = _index_entry_from_record(record, rel_note_path)
            entry["sr"] = existing.get("sr", entry["sr"])
            entry["notebooks"] = existing.get("notebooks", [])
            index["questions"][qid] = entry
        else:
            index["questions"][qid] = _index_entry_from_record(record, rel_note_path)

        added_ids.append(qid)

    save_index(bank_dir, index)
    for qid in added_ids:
        print(qid)
    return 0


def _filter_questions(
    questions: dict[str, Any],
    category: str | None,
    difficulty: str | None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    out = []
    for entry in questions.values():
        if category and entry.get("category") != category:
            continue
        if difficulty and entry.get("difficulty") != difficulty:
            continue
        if tag and tag not in (entry.get("tags") or []):
            continue
        out.append(entry)
    return out


def _select_for_notebook(
    index: dict[str, Any],
    category: str | None,
    difficulty: str | None,
    num: int,
    ids: list[str] | None,
    as_of: str,
) -> list[dict[str, Any]]:
    questions = index["questions"]
    if ids:
        selected = []
        for qid in ids:
            if qid not in questions:
                raise ValueError(f"unknown question id: {qid}")
            selected.append(questions[qid])
        return selected

    candidates = _filter_questions(questions, category, difficulty)
    as_of_date = _parse_iso(as_of)

    def is_due(entry: dict[str, Any]) -> bool:
        nrd = entry.get("sr", {}).get("next_review_date")
        if not nrd:
            return True
        return _parse_iso(nrd) <= as_of_date

    def is_unseen(entry: dict[str, Any]) -> bool:
        return int(entry.get("sr", {}).get("reps", 0)) == 0

    due = [e for e in candidates if is_due(e)]
    not_due = [e for e in candidates if not is_due(e)]

    # Due first (earliest next_review_date), then unseen, then the rest.
    due.sort(key=lambda e: (e.get("sr", {}).get("next_review_date") or "", e["id"]))
    not_due.sort(key=lambda e: (not is_unseen(e), e["id"]))

    ordered = due + not_due
    return ordered[:num]


def _question_dict_from_entry(bank_dir: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Merge index metadata with full content recovered from the bank note."""
    note_path = bank_dir / entry["note_path"]
    content = read_bank_note(note_path) if note_path.exists() else {}
    return {
        "id": entry["id"],
        "title": entry["title"],
        "tags": entry.get("tags", []),
        "prompt": content.get("prompt", ""),
        "input_preview": content.get("input_preview", ""),
        "expected": content.get("expected", ""),
        "setup": content.get("setup", ""),
        "examples": content.get("examples", ""),
        "constraints": content.get("constraints", ""),
        "solution": content.get("solution", ""),
        "complexity": content.get("complexity", ""),
        "staff_signals": content.get("staff_signals", ""),
    }


def cmd_generate_notebook(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    date = today_iso(args.date)
    index = load_index(bank_dir)

    ids = [s.strip() for s in args.ids.split(",")] if args.ids else None
    if ids:
        ids = [s for s in ids if s]

    try:
        selected = _select_for_notebook(
            index, args.category, args.difficulty, args.num, ids, date
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not selected:
        print("error: no questions matched the selection criteria", file=sys.stderr)
        return 1

    title = args.title or f"DS Python Drill — {date}"
    intro = (
        "Practice notebook. Fill in each code cell with your answer. "
        "The companion `_KEY` notebook holds model solutions."
    )

    # Merge index metadata (title/tags) with full content recovered from the
    # bank note (prompt/examples/constraints/solution/notes).
    question_dicts = [_question_dict_from_entry(bank_dir, entry) for entry in selected]

    working_nb = notebook_builder.build_notebook(
        title, intro, question_dicts, include_solutions=False
    )
    key_nb = notebook_builder.build_notebook(
        f"{title} (KEY)", intro, question_dicts, include_solutions=True
    )

    notebooks_dir = _bank_subdir(bank_dir, "Notebooks")
    working_name = f"drill_{date}.ipynb"
    key_name = f"drill_{date}_KEY.ipynb"
    working_path = notebooks_dir / working_name
    key_path = notebooks_dir / key_name

    notebook_builder.write_notebook(working_nb, working_path)
    notebook_builder.write_notebook(key_nb, key_path)

    for entry in selected:
        nbs = entry.setdefault("notebooks", [])
        if working_name not in nbs:
            nbs.append(working_name)
    save_index(bank_dir, index)

    print(working_path)
    print(key_path)
    print("Selected questions:")
    for i, entry in enumerate(selected, start=1):
        print(f"  Q{i}: {entry['id']} — {entry['title']}")
    return 0


def cmd_append_notebook(args: argparse.Namespace) -> int:
    """Append already-banked questions (e.g. follow-ups) to an existing notebook."""
    bank_dir = resolve_bank_dir(args.bank_dir)
    index = load_index(bank_dir)

    working_path = Path(args.notebook).expanduser()
    if not working_path.exists():
        print(f"error: notebook not found: {working_path}", file=sys.stderr)
        return 1

    ids = [s.strip() for s in (args.ids or "").split(",") if s.strip()]
    if not ids:
        print("error: --ids is required (comma-separated question ids to append)",
              file=sys.stderr)
        return 2

    selected: list[dict[str, Any]] = []
    for qid in ids:
        if qid not in index["questions"]:
            print(f"error: unknown question id: {qid}", file=sys.stderr)
            return 1
        selected.append(index["questions"][qid])

    question_dicts = [_question_dict_from_entry(bank_dir, entry) for entry in selected]

    # Number the new questions one past the current maximum, and keep the WORKING
    # and KEY notebooks in lockstep by sharing that starting index.
    working_nb = notebook_builder.read_notebook(working_path)
    start_index = notebook_builder.max_question_number(working_nb) + 1
    notebook_builder.append_questions(
        working_nb, question_dicts, include_solutions=False, start_index=start_index
    )
    notebook_builder.write_notebook(working_nb, working_path)

    key_path = working_path.with_name(f"{working_path.stem}_KEY{working_path.suffix}")
    if key_path.exists():
        key_nb = notebook_builder.read_notebook(key_path)
        notebook_builder.append_questions(
            key_nb, question_dicts, include_solutions=True, start_index=start_index
        )
        notebook_builder.write_notebook(key_nb, key_path)

    for entry in selected:
        nbs = entry.setdefault("notebooks", [])
        if working_path.name not in nbs:
            nbs.append(working_path.name)
    save_index(bank_dir, index)

    print(working_path)
    if key_path.exists():
        print(key_path)
    print(f"Appended {len(selected)} question(s) starting at Q{start_index}:")
    for offset, entry in enumerate(selected):
        print(f"  Q{start_index + offset}: {entry['id']} — {entry['title']}")
    return 0


def cmd_due(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    as_of = today_iso(args.as_of)
    as_of_date = _parse_iso(as_of)
    index = load_index(bank_dir)

    candidates = _filter_questions(index["questions"], args.category, args.difficulty)
    due = []
    for entry in candidates:
        nrd = entry.get("sr", {}).get("next_review_date")
        if not nrd or _parse_iso(nrd) <= as_of_date:
            due.append(entry)

    due.sort(key=lambda e: (e.get("sr", {}).get("next_review_date") or "", e["id"]))
    if args.limit:
        due = due[: args.limit]

    print(f"{'ID':<32} {'CAT':<8} {'DIFF':<8} {'NEXT':<12} TITLE")
    for entry in due:
        nrd = entry.get("sr", {}).get("next_review_date") or "-"
        print(f"{entry['id']:<32} {entry['category']:<8} {entry['difficulty']:<8} "
              f"{nrd:<12} {entry['title']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    index = load_index(bank_dir)
    matches = _filter_questions(index["questions"], args.category, args.difficulty, args.tag)
    matches.sort(key=lambda e: e["id"])

    print(f"{'ID':<32} {'CAT':<8} {'DIFF':<8} TITLE")
    for entry in matches:
        print(f"{entry['id']:<32} {entry['category']:<8} {entry['difficulty']:<8} "
              f"{entry['title']}")
    return 0


def cmd_parse_notebook(args: argparse.Namespace) -> int:
    result = notebook_builder.parse_notebook(args.notebook)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_grade(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    today = today_iso(args.as_of)
    index = load_index(bank_dir)

    qid = args.id
    if qid not in index["questions"]:
        print(f"error: unknown question id: {qid}", file=sys.stderr)
        return 1
    if args.grade not in GRADES:
        print(f"error: grade must be one of {sorted(GRADES)}", file=sys.stderr)
        return 2

    entry = index["questions"][qid]
    sr = entry.setdefault("sr", new_sr_block(today))
    apply_grade(sr, args.grade, today)
    if args.notes:
        sr["history"][-1]["notes"] = args.notes

    save_index(bank_dir, index)
    print(json.dumps(sr, indent=2, ensure_ascii=False))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    bank_dir = resolve_bank_dir(args.bank_dir)
    today = today_iso(getattr(args, "as_of", None))
    today_date = _parse_iso(today)
    index = load_index(bank_dir)
    questions = index["questions"]

    total = len(questions)
    by_category: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    due_today = 0
    lapses_by_tag: dict[str, int] = {}

    for entry in questions.values():
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
        by_difficulty[entry["difficulty"]] = by_difficulty.get(entry["difficulty"], 0) + 1

        nrd = entry.get("sr", {}).get("next_review_date")
        if not nrd or _parse_iso(nrd) <= today_date:
            due_today += 1

        history = entry.get("sr", {}).get("history", [])
        lapse_count = sum(1 for h in history if h.get("grade") in ("again", "hard"))
        if lapse_count:
            for tag in entry.get("tags", []):
                lapses_by_tag[tag] = lapses_by_tag.get(tag, 0) + lapse_count

    print(f"Total questions: {total}")
    print("By category:")
    for cat in sorted(by_category):
        print(f"  {cat}: {by_category[cat]}")
    print("By difficulty:")
    for diff in sorted(by_difficulty):
        print(f"  {diff}: {by_difficulty[diff]}")
    print(f"Due today ({today}): {due_today}")

    print("Weakest tags (most lapses):")
    weakest = sorted(lapses_by_tag.items(), key=lambda kv: (-kv[1], kv[0]))
    if weakest:
        for tag, count in weakest[:10]:
            print(f"  {tag}: {count}")
    else:
        print("  (none yet)")
    return 0


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #
def _add_bank_dir_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bank-dir",
        default=None,
        help=(
            "Bank directory. Resolution order: this flag > env "
            f"{ENV_BANK_DIR} > {DEFAULT_BANK_DIRNAME}"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ds_python_interview_cli.py",
        description="Practice Python data-science interview questions with spaced repetition.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Register/persist a question (or batch).")
    _add_bank_dir_flag(p_add)
    p_add.add_argument("--from-json", help="JSON file: object or array of question objects.")
    p_add.add_argument("--update", action="store_true", help="Overwrite an existing id.")
    p_add.add_argument("--date", help="Override creation date (YYYY-MM-DD).")
    p_add.add_argument("--category")
    p_add.add_argument("--difficulty")
    p_add.add_argument("--title")
    p_add.add_argument("--prompt", default="")
    p_add.add_argument("--input-preview", dest="input_preview", default="")
    p_add.add_argument("--expected", default="")
    p_add.add_argument("--setup", default="")
    p_add.add_argument("--examples", default="")
    p_add.add_argument("--constraints", default="")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--source", default="")
    p_add.add_argument("--parent", default="", help="Parent question id (for follow-ups).")
    p_add.add_argument("--solution", default="")
    p_add.add_argument("--complexity", default="")
    p_add.add_argument("--staff-signals", dest="staff_signals", default="")
    p_add.set_defaults(func=cmd_add)

    # generate-notebook
    p_gen = sub.add_parser("generate-notebook", help="Build WORKING and KEY drill notebooks.")
    _add_bank_dir_flag(p_gen)
    p_gen.add_argument("--category")
    p_gen.add_argument("--difficulty")
    p_gen.add_argument("--num", type=int, default=5)
    p_gen.add_argument("--ids", help="Comma-separated ids, used in order.")
    p_gen.add_argument("--title")
    p_gen.add_argument("--date", help="Notebook date (YYYY-MM-DD), default today.")
    p_gen.set_defaults(func=cmd_generate_notebook)

    # append-notebook
    p_app = sub.add_parser(
        "append-notebook",
        help="Append banked questions (e.g. follow-ups) to an existing notebook.",
    )
    _add_bank_dir_flag(p_app)
    p_app.add_argument("--notebook", required=True,
                       help="Path to the WORKING .ipynb to append to (KEY updated too).")
    p_app.add_argument("--ids", required=True,
                       help="Comma-separated question ids to append, in order.")
    p_app.set_defaults(func=cmd_append_notebook)

    # due
    p_due = sub.add_parser("due", help="List questions due for review.")
    _add_bank_dir_flag(p_due)
    p_due.add_argument("--category")
    p_due.add_argument("--difficulty")
    p_due.add_argument("--limit", type=int)
    p_due.add_argument("--as-of", dest="as_of", help="As-of date (YYYY-MM-DD), default today.")
    p_due.set_defaults(func=cmd_due)

    # list
    p_list = sub.add_parser("list", help="List bank questions.")
    _add_bank_dir_flag(p_list)
    p_list.add_argument("--category")
    p_list.add_argument("--difficulty")
    p_list.add_argument("--tag")
    p_list.set_defaults(func=cmd_list)

    # parse-notebook
    p_parse = sub.add_parser("parse-notebook", help="Parse a completed notebook to JSON.")
    _add_bank_dir_flag(p_parse)
    p_parse.add_argument("--notebook", required=True, help="Path to a .ipynb file.")
    p_parse.set_defaults(func=cmd_parse_notebook)

    # grade
    p_grade = sub.add_parser("grade", help="Apply a spaced-repetition grade.")
    _add_bank_dir_flag(p_grade)
    p_grade.add_argument("--id", required=True)
    p_grade.add_argument("--grade", required=True, choices=sorted(GRADES))
    p_grade.add_argument("--notes", default="")
    p_grade.add_argument("--as-of", dest="as_of", help="As-of date (YYYY-MM-DD), default today.")
    p_grade.set_defaults(func=cmd_grade)

    # stats
    p_stats = sub.add_parser("stats", help="Print bank statistics.")
    _add_bank_dir_flag(p_stats)
    p_stats.add_argument("--as-of", dest="as_of", help="As-of date (YYYY-MM-DD), default today.")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
