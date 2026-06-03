"""Build and parse nbformat v4 Jupyter notebooks using only the standard library.

A ``.ipynb`` file is just JSON, so this module constructs and reads the notebook
dicts directly. No third-party packages (nbformat, etc.) are required.
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


def _code_cell(text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "id": _new_id(),
        "metadata": {},
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

    examples = (question.get("examples") or "").strip()
    if examples:
        parts.append("**Examples**")
        parts.append("")
        parts.append(examples)
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


def build_notebook(
    title: str,
    intro_md: str,
    questions: list[dict[str, Any]],
    include_solutions: bool,
) -> dict[str, Any]:
    """Build an nbformat v4 notebook dict.

    When ``include_solutions`` is False a WORKING notebook is produced: each
    question gets a placeholder code cell for the user to fill in. When True a
    KEY notebook is produced: code cells carry the model solution and a trailing
    markdown cell holds complexity / staff-signal notes.
    """
    cells: list[dict[str, Any]] = []

    intro_text = title.rstrip()
    extra = (intro_md or "").strip()
    if extra:
        intro_text = f"{intro_text}\n\n{extra}"
    cells.append(_markdown_cell(intro_text))

    for i, question in enumerate(questions, start=1):
        cells.append(_markdown_cell(_question_markdown(i, question)))
        if include_solutions:
            solution = question.get("solution") or ""
            if not solution.endswith("\n"):
                solution = solution + "\n"
            cells.append(_code_cell(solution))
            cells.append(_markdown_cell(_key_notes_markdown(question)))
        else:
            cells.append(_code_cell(f"# Your answer for Q{i}\n"))

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


_Q_HEADER_RE = re.compile(r"^##\s*Q(\d+)\s*—\s*(.*?)\s*$")


def _cell_source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return source


def parse_notebook(path) -> list[dict[str, Any]]:
    """Parse a (possibly user-completed) notebook into question answers.

    Walks the cells in order. Whenever a markdown cell starts with
    ``## Q{n} —`` the following code cell's joined source is captured as that
    question's ``answer_code``.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        nb = json.load(fh)

    results: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None

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
            if pending is not None:
                results.append(
                    {
                        "qnum": pending["qnum"],
                        "title": pending["title"],
                        "answer_code": text,
                    }
                )
                pending = None

    return results
