#!/usr/bin/env python3
"""Self-contained unittest suite for the DS Python interview CLI.

Run directly:  python3 scripts/tests/test_cli.py -v
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

# Make the scripts directory importable regardless of CWD.
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(_TESTS_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import ds_python_interview_cli as cli  # noqa: E402
import notebook_builder  # noqa: E402


SAMPLE_QUESTIONS = [
    {
        "category": "dsa",
        "difficulty": "easy",
        "title": "Two Sum",
        "prompt": "Return indices of two numbers that add up to target.",
        "examples": "nums=[2,7,11,15], target=9 -> [0,1]",
        "constraints": "Exactly one solution.",
        "tags": ["hash-map", "arrays"],
        "source": "classic",
        "solution": "def two_sum(nums, target):\n    seen = {}\n    return seen",
        "complexity": "O(n) time, O(n) space",
        "staff_signals": "Mentions hash map trade-off.",
    },
    {
        "category": "pandas",
        "difficulty": "medium",
        "title": "Group By Mean",
        "prompt": "Compute the mean value per group.",
        "examples": "df.groupby('k')['v'].mean()",
        "constraints": "Use vectorized ops.",
        "tags": ["groupby", "aggregation"],
        "solution": "result = df.groupby('k')['v'].mean()",
        "complexity": "O(n)",
        "staff_signals": "Avoids Python loops.",
    },
    {
        "category": "stats",
        "difficulty": "hard",
        "title": "Bayes Update",
        "prompt": "Compute the posterior probability.",
        "examples": "P(A|B) = ...",
        "constraints": "Use Bayes rule.",
        "tags": ["probability", "bayes"],
        "solution": "posterior = (likelihood * prior) / evidence",
        "complexity": "O(1)",
        "staff_signals": "States assumptions clearly.",
    },
]


SETUP_QUESTION = {
    "category": "pandas",
    "difficulty": "easy",
    "title": "Sum Amounts",
    "prompt": "Return the total amount.",
    "input_preview": "orders:\n    amount\n    10\n    20",
    "expected": "30",
    "setup": "orders = pd.DataFrame({'amount': [10, 20]})\norders",
    "constraints": "Vectorize; no Python loops.",
    "tags": ["groupby", "sum"],
    "source": "generated",
    "solution": "total = orders['amount'].sum()",
    "complexity": "O(n)",
    "staff_signals": "Vectorized sum.",
}


def _role(cell: dict) -> str | None:
    return ((cell.get("metadata") or {}).get("ds_interview") or {}).get("role")


def run_cli(argv: list[str]) -> str:
    """Run the CLI and capture stdout; assert success exit code."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(argv)
    if rc != 0:
        raise AssertionError(f"CLI returned non-zero exit {rc} for argv={argv}")
    return buf.getvalue()


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.bank_dir = Path(self._tmp.name) / "interview_bank"
        # Write the sample JSON array.
        self.json_path = Path(self._tmp.name) / "questions.json"
        self.json_path.write_text(json.dumps(SAMPLE_QUESTIONS), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _bank(self, *args: str) -> list[str]:
        return ["--bank-dir", str(self.bank_dir), *args]

    def _add_all(self) -> None:
        run_cli(["add", *self._bank("--from-json", str(self.json_path),
                                    "--date", "2026-01-01")])

    def test_add_creates_notes_and_index(self) -> None:
        self._add_all()

        bank_notes = list((self.bank_dir / "Bank").glob("*.md"))
        self.assertEqual(len(bank_notes), 3)

        index = json.loads((self.bank_dir / "_index.json").read_text())
        self.assertEqual(len(index["questions"]), 3)
        for entry in index["questions"].values():
            self.assertIn("sr", entry)
            self.assertEqual(entry["sr"]["ease"], 2.5)
            self.assertEqual(entry["sr"]["reps"], 0)
            self.assertEqual(entry["sr"]["next_review_date"], "2026-01-01")

    def test_generate_notebook(self) -> None:
        self._add_all()
        run_cli(["generate-notebook",
                 *self._bank("--num", "3", "--date", "2026-01-02")])

        working = self.bank_dir / "Notebooks" / "drill_2026-01-02.ipynb"
        key = self.bank_dir / "Notebooks" / "drill_2026-01-02_KEY.ipynb"
        self.assertTrue(working.exists())
        self.assertTrue(key.exists())

        working_nb = json.loads(working.read_text())
        key_nb = json.loads(key.read_text())
        self.assertEqual(working_nb["nbformat"], 4)
        self.assertEqual(key_nb["nbformat"], 4)

        # Verify sequential Q markdown each followed by a placeholder code cell.
        cells = working_nb["cells"]
        q_markers = []
        for idx, cell in enumerate(cells):
            src = "".join(cell["source"])
            if cell["cell_type"] == "markdown" and src.startswith("## Q"):
                q_markers.append((idx, src))
                # Next cell must be a code cell with the placeholder only.
                nxt = cells[idx + 1]
                self.assertEqual(nxt["cell_type"], "code")
                code_src = "".join(nxt["source"])
                self.assertIn("# Your answer for", code_src)
                self.assertNotIn("def two_sum", code_src)
                self.assertNotIn("groupby", code_src)

        self.assertTrue(q_markers[0][1].startswith("## Q1"))
        self.assertTrue(q_markers[1][1].startswith("## Q2"))
        self.assertTrue(q_markers[2][1].startswith("## Q3"))
        self.assertEqual(len(q_markers), 3)

        # KEY notebook code cells contain real solution code.
        key_code = [
            "".join(c["source"]) for c in key_nb["cells"] if c["cell_type"] == "code"
        ]
        all_key_code = "\n".join(key_code)
        self.assertIn("def two_sum", all_key_code)
        self.assertIn("groupby", all_key_code)
        self.assertIn("posterior", all_key_code)

    def test_parse_notebook_with_injected_answers(self) -> None:
        self._add_all()
        run_cli(["generate-notebook",
                 *self._bank("--num", "3", "--date", "2026-01-02")])
        working = self.bank_dir / "Notebooks" / "drill_2026-01-02.ipynb"

        nb = json.loads(working.read_text())
        injected = {}
        counter = 0
        for idx, cell in enumerate(nb["cells"]):
            if cell["cell_type"] == "markdown" and "".join(cell["source"]).startswith("## Q"):
                counter += 1
                code_cell = nb["cells"][idx + 1]
                answer = f"answer_value_{counter} = {counter}\n"
                code_cell["source"] = [answer]
                injected[counter] = answer

        copy_path = self.bank_dir / "Notebooks" / "drill_2026-01-02_done.ipynb"
        copy_path.write_text(json.dumps(nb), encoding="utf-8")

        out = run_cli(["parse-notebook", *self._bank("--notebook", str(copy_path))])
        parsed = json.loads(out)
        self.assertEqual(len(parsed), 3)
        for item in parsed:
            self.assertEqual(item["answer_code"], injected[item["qnum"]])

    def test_grade_progression(self) -> None:
        self._add_all()
        index = json.loads((self.bank_dir / "_index.json").read_text())
        qid = next(iter(index["questions"]))

        out1 = run_cli(["grade", *self._bank("--id", qid, "--grade", "good",
                                             "--as-of", "2026-01-01")])
        sr1 = json.loads(out1)
        self.assertEqual(sr1["interval_days"], 1)
        self.assertEqual(sr1["next_review_date"], "2026-01-02")

        out2 = run_cli(["grade", *self._bank("--id", qid, "--grade", "good",
                                             "--as-of", "2026-01-02")])
        sr2 = json.loads(out2)
        self.assertEqual(sr2["interval_days"], 6)
        self.assertGreater(
            cli._parse_iso(sr2["next_review_date"]),
            cli._parse_iso(sr1["next_review_date"]),
        )

        out3 = run_cli(["grade", *self._bank("--id", qid, "--grade", "again",
                                             "--as-of", "2026-01-08")])
        sr3 = json.loads(out3)
        self.assertEqual(sr3["interval_days"], 1)
        self.assertEqual(sr3["reps"], 0)
        self.assertEqual(sr3["next_review_date"], "2026-01-09")

    def test_stats_reports_three(self) -> None:
        self._add_all()
        out = run_cli(["stats", *self._bank("--as-of", "2026-01-01")])
        self.assertIn("Total questions: 3", out)
        self.assertIn("dsa: 1", out)
        self.assertIn("pandas: 1", out)
        self.assertIn("stats: 1", out)

    def test_setup_cells_and_roundtrip(self) -> None:
        # A question that ships a runnable setup + input preview + expected output.
        qpath = Path(self._tmp.name) / "setupq.json"
        qpath.write_text(json.dumps([SETUP_QUESTION]), encoding="utf-8")
        run_cli(["add", *self._bank("--from-json", str(qpath), "--date", "2026-01-01")])

        # Bank note round-trips the new fields.
        note = next((self.bank_dir / "Bank").glob("*.md"))
        content = cli.read_bank_note(note)
        self.assertIn("pd.DataFrame", content["setup"])
        self.assertEqual(content["expected"], "30")
        self.assertIn("orders:", content["input_preview"])

        run_cli(["generate-notebook",
                 *self._bank("--num", "1", "--date", "2026-01-03")])
        working = self.bank_dir / "Notebooks" / "drill_2026-01-03.ipynb"
        nb = json.loads(working.read_text())

        roles = [_role(c) for c in nb["cells"] if c["cell_type"] == "code"]
        self.assertIn("imports", roles)   # pandas import derived from setup
        self.assertIn("setup", roles)
        self.assertIn("answer", roles)

        setup_cell = next(c for c in nb["cells"] if _role(c) == "setup")
        self.assertIn("pd.DataFrame", "".join(setup_cell["source"]))

        answer_cell = next(c for c in nb["cells"] if _role(c) == "answer")
        answer_src = "".join(answer_cell["source"])
        self.assertIn("# Your answer", answer_src)
        self.assertNotIn("sum()", answer_src)  # no solution leakage

        markdown = "\n".join(
            "".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown"
        )
        self.assertIn("Input data", markdown)
        self.assertIn("Expected output", markdown)

        # parse-notebook must return the ANSWER cell, not the setup cell.
        for c in nb["cells"]:
            if _role(c) == "answer":
                c["source"] = ["my_answer = 42\n"]
        done = self.bank_dir / "Notebooks" / "drill_2026-01-03_done.ipynb"
        done.write_text(json.dumps(nb), encoding="utf-8")
        parsed = json.loads(
            run_cli(["parse-notebook", *self._bank("--notebook", str(done))])
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["answer_code"], "my_answer = 42\n")

        # KEY notebook carries the solution in its answer cell.
        key = self.bank_dir / "Notebooks" / "drill_2026-01-03_KEY.ipynb"
        key_nb = json.loads(key.read_text())
        key_answer = next(c for c in key_nb["cells"] if _role(c) == "answer")
        self.assertIn("sum()", "".join(key_answer["source"]))

    def test_bank_dir_env_override(self) -> None:
        # Flag should win over env; env should win over default.
        old = os.environ.get(cli.ENV_BANK_DIR)
        try:
            os.environ[cli.ENV_BANK_DIR] = "env_only_bank"
            resolved = cli.resolve_bank_dir(str(self.bank_dir))
            self.assertEqual(resolved, self.bank_dir)
            env_resolved = cli.resolve_bank_dir(None)
            self.assertEqual(str(env_resolved), "env_only_bank")
        finally:
            if old is None:
                os.environ.pop(cli.ENV_BANK_DIR, None)
            else:
                os.environ[cli.ENV_BANK_DIR] = old


if __name__ == "__main__":
    unittest.main()
