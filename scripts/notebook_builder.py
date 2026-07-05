"""Build and parse nbformat v4 Jupyter notebooks using only the standard library.

A ``.ipynb`` file is just JSON, so this module constructs and reads the notebook
dicts directly. No third-party packages (nbformat, etc.) are required.

Each generated question contributes up to three cells:

1. a markdown prompt cell (`## Q{n} — Title`, including an **Input data** preview
   and the **Expected output**),
2. a runnable **setup** code cell that constructs the dataset for the question so
   the user can execute it and experiment with real data, and
3. an **answer** code cell (empty in the WORKING notebook, the model solution in
   the KEY notebook).

Code cells are tagged in their metadata (``metadata.ds_interview.role``) so a
completed notebook can be parsed back to the user's answers unambiguously, even
though setup cells are also code.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any


def _new_id() -> str:
    """Return a short, unique cell id."""
    return uuid.uuid4().hex[:8]


def _as_source_lines(text: str) -> list[str]:
    """Split text into nbformat-style ``source`` lines.

    Each line keeps its trailing newline except (possibly) the last one, which
    matches how Jupyter stores multi-line sources.
    """
    if text == "":
        return []
    lines = text.splitlines(keepends=True)
    return lines


def _markdown_cell(text: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": _new_id(),
        "metadata": {},
        "source": _as_source_lines(text),
    }


def _code_cell(text: str, role: str | None = None, qnum: int | None = None) -> dict[str, Any]:
    """Build a code cell, optionally tagged with a ``ds_interview`` role.

    ``role`` is one of ``"imports"``, ``"setup"``, or ``"answer"``. The role (and
    question number) live in ``metadata`` so ``parse_notebook`` can reliably
    distinguish the user's answer cell from setup/imports cells.
    """
    metadata: dict[str, Any] = {}
    if role is not None:
        tag: dict[str, Any] = {"role": role}
        if qnum is not None:
            tag["qnum"] = qnum
        metadata["ds_interview"] = tag
    return {
        "cell_type": "code",
        "id": _new_id(),
        "metadata": metadata,
        "execution_count": None,
        "outputs": [],
        "source": _as_source_lines(text),
    }


def _question_markdown(index: int, question: dict[str, Any]) -> str:
    """Render the prompt markdown for a single question."""
    title = question.get("title", "").strip()
    parts: list[str] = [f"## Q{index} — {title}", ""]

    prompt = (question.get("prompt") or "").strip()
    if prompt:
        parts.append(prompt)
        parts.append("")

    input_preview = (question.get("input_preview") or "").strip()
    if input_preview:
        parts.append("**Input data**")
        parts.append("")
        parts.append(input_preview)
        parts.append("")

    expected = (question.get("expected") or "").strip()
    if expected:
        parts.append("**Expected output**")
        parts.append("")
        parts.append(expected)
        parts.append("")

    # Legacy combined examples block (kept for backward compatibility).
    examples = (question.get("examples") or "").strip()
    if examples:
        parts.append("**Examples**")
        parts.append("")
        parts.append(examples)
        parts.append("")

    setup = (question.get("setup") or "").strip()
    if setup:
        parts.append(
            "_Run the **setup** cell below to build and preview the data, "
            "then write your answer in the next cell._"
        )
        parts.append("")

    constraints = (question.get("constraints") or "").strip()
    if constraints:
        parts.append("**Constraints**")
        parts.append("")
        parts.append(constraints)
        parts.append("")

    tags = question.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    parts.append(f"Tags: {', '.join(tags)}")

    return "\n".join(parts)


def _key_notes_markdown(question: dict[str, Any]) -> str:
    complexity = (question.get("complexity") or "").strip()
    staff_signals = (question.get("staff_signals") or "").strip()
    parts = ["**Notes**", ""]
    parts.append(f"**Complexity:** {complexity}")
    parts.append("")
    parts.append(f"**Staff signals:** {staff_signals}")
    return "\n".join(parts)


def _requirements_for(questions: list[dict[str, Any]]) -> str:
    """Derive a Requirements section for the intro cell from question code."""
    blob = "\n".join(
        (q.get("setup") or "") + "\n" + (q.get("solution") or "") for q in questions
    )
    lines = ["**Requirements** — to run this notebook you need:", ""]
    lines.append("- Python 3.10+ with **Jupyter** (JupyterLab, `jupyter notebook`, or VS Code)")
    if "pd." in blob or "pandas" in blob:
        lines.append("- `pandas` — `pip install pandas`")
    if "np." in blob or "numpy" in blob:
        lines.append("- `numpy` — `pip install numpy`")
    if "scipy" in blob:
        lines.append("- `scipy` — `pip install scipy`")
    if "statsmodels" in blob:
        lines.append("- `statsmodels` — `pip install statsmodels`")
    if "sqlite3" in blob or "duckdb" in blob:
        lines.append(
            "- SQL questions run on `sqlite3` (Python standard library — nothing to"
            " install); *optional:* `pip install duckdb` to get a Postgres-style"
            " dialect instead (the setup cell auto-detects it)"
        )
    return "\n".join(lines)


def _imports_for(questions: list[dict[str, Any]]) -> str:
    """Derive a shared imports cell from what the setup code actually uses."""
    blob = "\n".join((q.get("setup") or "") for q in questions)
    lines: list[str] = []
    if "pd." in blob or "pandas" in blob:
        lines.append("import pandas as pd")
    if "np." in blob or "numpy" in blob:
        lines.append("import numpy as np")
    if "sqlite3" in blob:
        lines.append("import sqlite3")
    return "\n".join(lines)


def _question_cells(
    index: int, question: dict[str, Any], include_solutions: bool
) -> list[dict[str, Any]]:
    """Build the cells for a single question: prompt, optional setup, answer."""
    cells: list[dict[str, Any]] = [_markdown_cell(_question_markdown(index, question))]

    setup = (question.get("setup") or "").strip()
    if setup:
        if not setup.endswith("\n"):
            setup = setup + "\n"
        cells.append(_code_cell(setup, role="setup", qnum=index))

    if include_solutions:
        solution = question.get("solution") or ""
        if not solution.endswith("\n"):
            solution = solution + "\n"
        cells.append(_code_cell(solution, role="answer", qnum=index))
        cells.append(_markdown_cell(_key_notes_markdown(question)))
    else:
        cells.append(_code_cell(f"# Your answer for Q{index}\n", role="answer", qnum=index))

    return cells


def build_notebook(
    title: str,
    intro_md: str,
    questions: list[dict[str, Any]],
    include_solutions: bool,
) -> dict[str, Any]:
    """Build an nbformat v4 notebook dict.

    The notebook opens with an intro cell and, if any question ships a ``setup``,
    a shared imports cell. Each question then contributes a markdown prompt, an
    optional runnable setup cell, and an answer cell. When ``include_solutions``
    is False a WORKING notebook is produced (empty answer cells); when True a KEY
    notebook is produced (model solutions plus complexity / staff-signal notes).
    """
    cells: list[dict[str, Any]] = []

    intro_text = title.rstrip()
    extra = (intro_md or "").strip()
    if extra:
        intro_text = f"{intro_text}\n\n{extra}"
    requirements = _requirements_for(questions)
    if requirements:
        intro_text = f"{intro_text}\n\n{requirements}"
    cells.append(_markdown_cell(intro_text))

    imports = _imports_for(questions)
    if imports:
        cells.append(_code_cell(imports + "\n", role="imports"))

    for i, question in enumerate(questions, start=1):
        cells.extend(_question_cells(i, question, include_solutions))

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook(nb: dict[str, Any], path) -> None:
    """Atomically write a notebook dict as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(nb, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_name, str(path))
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def read_notebook(path) -> dict[str, Any]:
    """Load a notebook JSON file into a dict."""
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


_Q_HEADER_RE = re.compile(r"^##\s*Q(\d+)\s*—\s*(.*?)\s*$")


def max_question_number(nb: dict[str, Any]) -> int:
    """Return the highest ``## Q{n}`` number present in the notebook (0 if none)."""
    highest = 0
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        text = _cell_source_text(cell)
        first_line = text.splitlines()[0] if text else ""
        match = _Q_HEADER_RE.match(first_line.strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def ensure_imports(nb: dict[str, Any], questions: list[dict[str, Any]]) -> None:
    """Insert any imports the new questions need that the notebook lacks.

    Appended questions may introduce pandas/numpy where the original notebook had
    none. A new imports cell is inserted just after the intro cell so the added
    setup cells run.
    """
    needed = _imports_for(questions)
    if not needed:
        return
    existing = "\n".join(
        _cell_source_text(c) for c in nb.get("cells", []) if c.get("cell_type") == "code"
    )
    missing = [line for line in needed.splitlines() if line and line not in existing]
    if not missing:
        return
    cells = nb.setdefault("cells", [])
    insert_at = 1 if cells and cells[0].get("cell_type") == "markdown" else 0
    cells.insert(insert_at, _code_cell("\n".join(missing) + "\n", role="imports"))


def append_questions(
    nb: dict[str, Any],
    questions: list[dict[str, Any]],
    include_solutions: bool,
    start_index: int | None = None,
) -> dict[str, Any]:
    """Append new questions to an existing notebook dict, continuing numbering.

    ``start_index`` defaults to one past the current highest question number.
    Pass it explicitly to keep a WORKING and KEY notebook numbered in lockstep.
    """
    ensure_imports(nb, questions)
    if start_index is None:
        start_index = max_question_number(nb) + 1
    cells = nb.setdefault("cells", [])
    for offset, question in enumerate(questions):
        cells.extend(_question_cells(start_index + offset, question, include_solutions))
    return nb


def _cell_source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return source


def parse_notebook(path) -> list[dict[str, Any]]:
    """Parse a (possibly user-completed) notebook into question answers.

    Walks the cells in order. Markdown ``## Q{n} —`` headers establish the
    current question. The user's answer is taken from the code cell whose
    metadata role is ``"answer"``; ``"imports"`` and ``"setup"`` code cells are
    skipped. For older notebooks without role metadata, the first code cell after
    a question header is used as a fallback.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        nb = json.load(fh)

    results: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    answered: set[int] = set()

    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type")
        text = _cell_source_text(cell)

        if cell_type == "markdown":
            first_line = text.splitlines()[0] if text else ""
            match = _Q_HEADER_RE.match(first_line.strip())
            if match:
                pending = {
                    "qnum": int(match.group(1)),
                    "title": match.group(2).strip(),
                }
            # Non-question markdown (intro, KEY notes) is ignored.
        elif cell_type == "code":
            tag = (cell.get("metadata") or {}).get("ds_interview") or {}
            role = tag.get("role")

            if role in ("imports", "setup"):
                continue

            if role == "answer":
                qnum = tag.get("qnum")
                title = pending["title"] if pending else ""
                if qnum is None and pending is not None:
                    qnum = pending["qnum"]
                results.append({"qnum": qnum, "title": title, "answer_code": text})
                if qnum is not None:
                    answered.add(qnum)
                pending = None
                continue

            # Legacy fallback: untagged code cell right after a question header.
            if pending is not None and pending["qnum"] not in answered:
                results.append(
                    {
                        "qnum": pending["qnum"],
                        "title": pending["title"],
                        "answer_code": text,
                    }
                )
                answered.add(pending["qnum"])
                pending = None

    return results
