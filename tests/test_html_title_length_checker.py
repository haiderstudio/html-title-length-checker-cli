"""Tests for html_title_length_checker.

Run from the repo root:

    python3 tests/test_html_title_length_checker.py
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "html_title_length_checker.py"

sys.path.insert(0, str(REPO / "src"))
import html_title_length_checker as tool  # noqa: E402


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return str(path)


def run_cli(args, input=None, cwd=None):
    result = subprocess.run(
        [sys.executable, str(SRC)] + args,
        cwd=cwd or str(REPO), capture_output=True, text=True,
        input=input)
    return result.returncode, result.stdout, result.stderr


def page(title, line_breaks=False):
    if line_breaks:
        return ("<html>\n<head>\n<title>\n  %s\n</title>\n"
                "</head></html>\n" % title)
    return "<html><head><title>%s</title></head></html>\n" % title


GOOD = "How to Grow Tomatoes at Home in Pots"  # 36 characters
EXACT_MIN = "How to Grow Tomatoes at Home!!"  # 30 characters
EXACT_MAX = ("Fresh Bread at Home: A Simple Guide "
             "for First-Time Bakers!!!")  # 60 characters
TOO_LONG = ("The Complete Step-by-Step Guide to Growing Organic "
            "Tomatoes at Home in Pots All Year Round")  # 90 characters


class TestCheckText(unittest.TestCase):
    def test_in_range_title_passes(self):
        bad, error = tool.check_text(page(GOOD))
        self.assertEqual((bad, error), ([], None))

    def test_exactly_minimum_passes(self):
        self.assertEqual(len(EXACT_MIN), 30)
        bad, error = tool.check_text(page(EXACT_MIN))
        self.assertEqual((bad, error), ([], None))

    def test_one_below_minimum_fails(self):
        short = EXACT_MIN[:-1]
        self.assertEqual(len(short), 29)
        bad, error = tool.check_text(page(short))
        self.assertIsNone(error)
        self.assertEqual(len(bad), 1)
        self.assertIn("29 characters long, shorter than the minimum 30",
                      bad[0]["reason"])

    def test_exactly_maximum_passes(self):
        self.assertEqual(len(EXACT_MAX), 60)
        bad, error = tool.check_text(page(EXACT_MAX))
        self.assertEqual((bad, error), ([], None))

    def test_one_above_maximum_fails(self):
        long_title = EXACT_MAX + "!"
        self.assertEqual(len(long_title), 61)
        bad, error = tool.check_text(page(long_title))
        self.assertEqual(len(bad), 1)
        self.assertIn("61 characters long, longer than the maximum 60",
                      bad[0]["reason"])

    def test_too_short_reports_line_and_length(self):
        bad, error = tool.check_text(page("Home"))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)
        self.assertIn('title is 4 characters long', bad[0]["reason"])

    def test_too_long_reports_length(self):
        self.assertEqual(len(TOO_LONG), 90)
        bad, error = tool.check_text(page(TOO_LONG))
        self.assertEqual(len(bad), 1)
        self.assertIn('title is 90 characters long, longer than the '
                      'maximum 60', bad[0]["reason"])

    def test_missing_title_reports_line_one(self):
        bad, error = tool.check_text("<html><head></head></html>\n")
        self.assertIsNone(error)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)
        self.assertIn("no <title> found", bad[0]["reason"])

    def test_empty_document_reports_missing_title(self):
        bad, error = tool.check_text("")
        self.assertEqual(len(bad), 1)
        self.assertIn("no <title> found", bad[0]["reason"])

    def test_empty_title_is_a_finding(self):
        bad, error = tool.check_text(page(""))
        self.assertEqual(len(bad), 1)
        self.assertIn("title is empty", bad[0]["reason"])

    def test_whitespace_only_title_is_empty(self):
        bad, error = tool.check_text(page("   \n  "))
        self.assertEqual(len(bad), 1)
        self.assertIn("title is empty", bad[0]["reason"])

    def test_title_on_a_later_line_reports_that_line(self):
        text = ("<!DOCTYPE html>\n<html>\n<head>\n"
                '<meta charset="utf-8">\n<title>Home</title>\n')
        bad, error = tool.check_text(text)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 5)

    def test_entity_counts_as_one_character(self):
        # Decoded length is 29 (fails); the raw "&amp;" is five
        # characters, so counting the raw text would pass.
        bad, error = tool.check_text(
            page("Tom &amp; Jerry: A Guide for Cook"))
        self.assertEqual(len(bad), 1)
        self.assertIn("29 characters long", bad[0]["reason"])

    def test_multiline_title_is_stripped(self):
        bad, error = tool.check_text(page(GOOD, line_breaks=True))
        self.assertEqual((bad, error), ([], None))

    def test_leading_and_trailing_whitespace_ignored(self):
        bad, error = tool.check_text(page("   " + GOOD + "  \n"))
        self.assertEqual((bad, error), ([], None))

    def test_multiple_titles_each_checked(self):
        text = (page("Home") + page(GOOD))
        bad, error = tool.check_text(text)
        self.assertEqual(len(bad), 1)
        self.assertIn("4 characters long", bad[0]["reason"])

    def test_two_bad_titles_both_reported_in_order(self):
        text = page("Home") + page(TOO_LONG)
        bad, error = tool.check_text(text)
        self.assertEqual(len(bad), 2)
        self.assertIn("shorter than", bad[0]["reason"])
        self.assertIn("longer than", bad[1]["reason"])

    def test_unclosed_title_is_still_measured(self):
        bad, error = tool.check_text(
            "<title>Unclosed title here is long enough yes")
        self.assertEqual((bad, error), ([], None))

    def test_unclosed_short_title_fails(self):
        bad, error = tool.check_text("<title>Short")
        self.assertEqual(len(bad), 1)
        self.assertIn("5 characters long", bad[0]["reason"])

    def test_self_closing_title_is_empty(self):
        bad, error = tool.check_text("<html><head><title/></head></html>\n")
        self.assertEqual(len(bad), 1)
        self.assertIn("title is empty", bad[0]["reason"])

    def test_uppercase_title_tag_is_checked(self):
        bad, error = tool.check_text(
            "<HTML><HEAD><TITLE>Home</TITLE></HEAD></HTML>\n")
        self.assertEqual(len(bad), 1)
        self.assertIn("4 characters long", bad[0]["reason"])

    def test_title_in_body_is_checked(self):
        bad, error = tool.check_text(
            "<html><body><title>Home</title></body></html>\n")
        self.assertEqual(len(bad), 1)
        self.assertIn("4 characters long", bad[0]["reason"])

    def test_nested_tag_inside_title_keeps_its_text(self):
        bad, error = tool.check_text(
            page("How to Grow <b>Tomatoes</b> at Home in Pots"))
        self.assertEqual((bad, error), ([], None))

    def test_non_english_title_counts_characters(self):
        title = "Comment faire pousser des tomates maison"
        self.assertEqual(len(title), 40)
        bad, error = tool.check_text(page(title))
        self.assertEqual((bad, error), ([], None))

    def test_custom_bounds_are_honoured(self):
        bad, error = tool.check_text(
            page("A Short Title!!"), 10, 20)
        self.assertEqual((bad, error), ([], None))
        bad, error = tool.check_text(page("Hello"), 5, 6)
        self.assertEqual((bad, error), ([], None))
        bad, error = tool.check_text(page(GOOD), 10, 20)
        self.assertEqual(len(bad), 1)
        self.assertIn("longer than the maximum 20", bad[0]["reason"])

    def test_min_larger_than_max_is_an_error(self):
        bad, error = tool.check_text(page(GOOD), 60, 30)
        self.assertEqual(bad, [])
        self.assertIn("larger than maximum", error)


class TestCli(unittest.TestCase):
    def test_clean_file_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page(GOOD))
            code, out, err = run_cli([path])
            self.assertEqual(code, 0)
            self.assertIn("every title is 30-60 characters long", out)

    def test_flagged_file_exits_one_with_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page("Home"))
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)
            self.assertIn('line 1 title is 4 characters long', out)
            self.assertIn("Checked 1 file(s), 1 title problem(s)", out)

    def test_folder_walks_html_and_htm_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page(GOOD))
            write(tmp, "b.htm", page("Home"))
            write(tmp, "notes.txt", page("Home"))
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("Checked 2 file(s), 1 title problem(s)", out)

    def test_no_recursive_stops_at_top_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page(GOOD))
            write(tmp, "sub/b.html", page("Home"))
            code, out, err = run_cli(["--no-recursive", tmp])
            self.assertEqual(code, 0)
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 1)

    def test_exclude_skips_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page(GOOD))
            write(tmp, "b.html", page("Home"))
            code, out, err = run_cli(["--exclude", "b.html", tmp])
            self.assertEqual(code, 0)

    def test_git_folder_never_walked(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page(GOOD))
            write(tmp, ".git/b.html", page("Home"))
            code, out, err = run_cli([tmp])
            self.assertEqual(code, 0)

    def test_file_given_directly_checked_whatever_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "data.txt", page("Home"))
            code, out, err = run_cli([path])
            self.assertEqual(code, 1)

    def test_missing_path_is_usage_error(self):
        code, out, err = run_cli(["no-such-file.html"])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_no_paths_is_usage_error(self):
        code, out, err = run_cli([])
        self.assertEqual(code, 2)
        self.assertIn("give a file or folder", err)

    def test_min_larger_than_max_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page(GOOD))
            code, out, err = run_cli(
                ["--min", "60", "--max", "30", path])
            self.assertEqual(code, 2)
            self.assertIn("larger than", err)

    def test_custom_bounds_via_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page("Home"))
            code, out, err = run_cli(
                ["--min", "1", "--max", "10", path])
            self.assertEqual(code, 0)

    def test_invalid_utf8_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.html"
            path.write_bytes(b'<title>\xff</title>\n')
            code, out, err = run_cli([str(path)])
            self.assertEqual(code, 1)
            self.assertIn("not valid UTF-8", out)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page("Home"))
            code, out, err = run_cli(["--json", path])
            self.assertEqual(code, 1)
            data = json.loads(out)
            self.assertEqual(data["checked"], 1)
            self.assertEqual(data["findings"], 1)
            self.assertEqual(data["files"][0]["findings"][0]["line"], 1)

    def test_stdin_clean(self):
        code, out, err = run_cli(["--stdin"], input=page(GOOD))
        self.assertEqual(code, 0)
        self.assertIn("every title is 30-60 characters long", out)

    def test_stdin_flagged(self):
        code, out, err = run_cli(["--stdin"], input=page(TOO_LONG))
        self.assertEqual(code, 1)
        self.assertIn('FAIL <stdin>: line 1 title is 90 characters long',
                      out)

    def test_stdin_missing_title(self):
        code, out, err = run_cli(
            ["--stdin"], input="<html><head></head></html>\n")
        self.assertEqual(code, 1)
        self.assertIn("no <title> found", out)

    def test_input_files_left_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page("Home"))
            before = Path(path).read_text()
            run_cli([path])
            self.assertEqual(Path(path).read_text(), before)

    def test_cli_runs_from_another_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", page(GOOD))
            result = subprocess.run(
                [sys.executable, str(SRC), "a.html"],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("every title is 30-60 characters long",
                          result.stdout)

    def test_cli_runs_under_fake_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.html", page(GOOD))
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                code, out, err = run_cli([path])
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
            self.assertEqual(code, 0)

    def test_version_flag(self):
        code, out, err = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("1.0.0", out)


class TestExamples(unittest.TestCase):
    def test_run_example_output_matches_sample(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        expected = (REPO / "examples/sample-output.md").read_text()
        self.assertEqual(result.stdout, expected)

    def test_readme_quotes_match_real_runs(self):
        readme = (REPO / "README.md").read_text()
        clean = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "examples/clean.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)
        self.assertIn(clean.stdout.strip(), readme)
        flagged = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(flagged.returncode, 1)
        self.assertIn(flagged.stdout.strip(), readme)
        folder = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "examples/"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(folder.returncode, 1)
        self.assertIn("Checked 3 file(s), 1 title problem(s) "
                      "in 1 file(s).", folder.stdout)
        self.assertIn("Checked 3 file(s), 1 title problem(s) "
                      "in 1 file(s).", readme)
        edge = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "examples/edge.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(edge.returncode, 0)
        self.assertIn(edge.stdout.strip(), readme)
        js = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "--json", "examples/flagged.html"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(js.returncode, 1)
        self.assertIn(js.stdout.strip(), readme)
        stdin_long = subprocess.run(
            [sys.executable, "src/html_title_length_checker.py",
             "--stdin"],
            input=("<!DOCTYPE html>\n<html><head><title>" + TOO_LONG
                   + "</title></head></html>\n"),
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(stdin_long.returncode, 1)
        self.assertIn(stdin_long.stdout.strip(), readme)


class TestHygiene(unittest.TestCase):
    def _repo_files(self, skip_tests=True, skip_examples=True):
        for root, dirs, files in os.walk(REPO):
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__")
                       and not (skip_tests and d == "tests")
                       and not (skip_examples and d == "examples")]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                yield Path(root) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "FIXME", "XXX"]
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for word in banned:
                if word in text:
                    hits.append("%s: %s" % (path.name, word))
        self.assertEqual(hits, [])

    def test_no_absolute_paths(self):
        hits = []
        for path in self._repo_files(skip_tests=True,
                                     skip_examples=False):
            text = path.read_text(errors="ignore")
            for marker in ("/home/", "/Users/", "C:\\"):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_no_real_secrets_outside_tests_and_examples(self):
        # The source holds no key values at all; the tests
        # and examples hold fake values only, so they are
        # excluded from this scan.
        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
            re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
            re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
            re.compile(r"AIza[0-9A-Za-z_-]{35}"),
            re.compile(r"[rs]k_(?:live|test)_[A-Za-z0-9]{16,}"),
            re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
            re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ"),
        ]
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append("%s: %s" % (path.name, pattern.pattern))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        stdlib = set(sys.stdlib_module_names)
        for target in (REPO / "src/html_title_length_checker.py",
                       REPO / "tests/test_html_title_length_checker.py"):
            tree = ast.parse(target.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(
                imported - stdlib - {"html_title_length_checker"},
                (target.name, imported))
            self.assertNotIn("yaml", imported)

    def test_no_network_use_in_src(self):
        src = (REPO / "src/html_title_length_checker.py").read_text()
        for marker in ("urllib.request", "requests", "socket",
                       "http.client", "urlopen", "urlretrieve"):
            self.assertNotIn(marker, src, marker)

    def test_gitignore_lists_env_first(self):
        lines = (REPO / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn("tests/test_html_title_length_checker.py", ci)
        self.assertIn("ubuntu-latest", ci)
        self.assertIn("3.12", ci)
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)

    def test_readme_names_the_neighbouring_repos(self):
        readme = (REPO / "README.md").read_text()
        self.assertIn("html-title-checker-cli", readme)
        self.assertIn("html-meta-description-checker-cli", readme)


if __name__ == "__main__":
    unittest.main()
