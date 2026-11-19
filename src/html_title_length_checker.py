#!/usr/bin/env python3
"""Check <title> text is 30-60 characters long.

Run: python3 src/html_title_length_checker.py page.html
     python3 src/html_title_length_checker.py --min 30 --max 60 pages/
     python3 src/html_title_length_checker.py --stdin < page.html

A title that is too short wastes the search snippet,
and a title that is too long gets cut off mid-word
in the results page - both are silent damage to how
a page shows up in search, found only when rankings
slip. This tool reads each HTML file, measures the
stripped text of every <title> element, and reports
each missing, empty or out-of-range title with the
file and the line, exiting 1, so it can fail a CI
run. A file whose titles are all 30-60 characters
long exits 0.

The bounds are inclusive: a title of exactly 30 or
exactly 60 characters passes. The length is measured
after stripping leading and trailing whitespace, and
after HTML entities are decoded, so "Tom &amp; Jerry"
counts the "&" as one character, not five.

A file given directly on the command line is always
checked, whatever its name. A folder is walked for
files ending in .html or .htm only, recursively by
default (--no-recursive stops at the top level). .git
folders are never walked, and directory links are
never followed.

It never rewrites a file, never touches the network,
and reads only the files and folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

__version__ = "1.0.0"

DEFAULT_MIN = 30
DEFAULT_MAX = 60
HTML_SUFFIXES = (".html", ".htm")


class _TitleParser(HTMLParser):
    """Collect every <title> element with its start line.

    HTMLParser reports the line of the current tag through
    getpos(), so the line recorded for a title is the line
    its opening tag sits on - the line the fix goes to.
    Entities are decoded by the parser itself, so the text
    measured is the text a browser shows.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag == "title" and self._current is None:
            self._current = {"line": self.getpos()[0], "parts": []}
        elif self._current is not None:
            # A tag inside a title is not title text; the
            # parser still reports its text through
            # handle_data, so nothing is lost.
            pass

    def handle_startendtag(self, tag, attrs):
        if tag == "title" and self._current is None:
            self.titles.append(
                {"line": self.getpos()[0], "text": ""})

    def handle_data(self, data):
        if self._current is not None:
            self._current["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "title" and self._current is not None:
            self.titles.append({
                "line": self._current["line"],
                "text": "".join(self._current["parts"]),
            })
            self._current = None

    def close(self):
        # A title never closed before the end of the file
        # still counts: its text is what the browser shows.
        # Flush the parser first: text after the last "<"
        # is only handed to handle_data by close(), so
        # finalising before that would measure an empty
        # title for a file whose title tag never closes.
        super().close()
        if self._current is not None:
            self.titles.append({
                "line": self._current["line"],
                "text": "".join(self._current["parts"]),
            })
            self._current = None


def check_text(text, min_length=DEFAULT_MIN, max_length=DEFAULT_MAX):
    """Check one document's text.

    Returns (findings, error): findings is a list of
    {"line": int, "reason": str} in document order, and
    error is None or a string saying why the file could
    not be checked at all.
    """
    if min_length > max_length:
        return [], ("minimum length %d is larger than maximum "
                    "length %d" % (min_length, max_length))
    parser = _TitleParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # HTMLParser is lenient; this is a guard.
        return [], "could not parse HTML: %s" % exc
    if not parser.titles:
        return [{
            "line": 1,
            "reason": "no <title> found",
        }], None
    findings = []
    for title in parser.titles:
        stripped = title["text"].strip()
        length = len(stripped)
        if length == 0:
            findings.append({
                "line": title["line"],
                "reason": "title is empty",
            })
        elif length < min_length:
            findings.append({
                "line": title["line"],
                "reason": ("title is %d characters long, shorter "
                           "than the minimum %d"
                           % (length, min_length)),
            })
        elif length > max_length:
            findings.append({
                "line": title["line"],
                "reason": ("title is %d characters long, longer "
                           "than the maximum %d"
                           % (length, max_length)),
            })
    return findings, None


def check_file(path, min_length=DEFAULT_MIN, max_length=DEFAULT_MAX):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    return check_text(text, min_length, max_length)


def _is_html_file(path):
    return Path(path).name.lower().endswith(HTML_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of HTML files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .html or
    .htm only. .git folders are never walked, and
    directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_html_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one title problem."""
    return ("FAIL %s: line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, min_length=DEFAULT_MIN, max_length=DEFAULT_MAX,
        recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path, min_length, max_length)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d title problem(s) "
                  "in %d file(s)."
                  % (len(files), findings, files_with_findings))
        else:
            print("OK — %d file(s) checked, every title is "
                  "%d-%d characters long."
                  % (len(files), min_length, max_length))
    return 1 if findings else 0


def run_stdin(min_length=DEFAULT_MIN, max_length=DEFAULT_MAX,
              as_json=False):
    """Check one HTML document read from standard input."""
    text = sys.stdin.read()
    bad, error = check_text(text, min_length, max_length)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": error}],
             "checked": 1, "findings": len(bad) + (1 if error else 0)},
            indent=2))
    else:
        if error:
            print("FAIL <stdin>: %s" % error)
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if not bad and not error:
            print("OK — 1 file(s) checked, every title is "
                  "%d-%d characters long."
                  % (min_length, max_length))
    return 1 if (bad or error) else 0


def build_parser():
    """The command-line parser, shared by main and tests."""
    parser = argparse.ArgumentParser(
        prog="html_title_length_checker",
        description="Check <title> text is 30-60 characters long.")
    parser.add_argument("paths", nargs="*", help="files or folders to check")
    parser.add_argument("--min", type=int, default=DEFAULT_MIN,
                        help="minimum title length (default 30)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help="maximum title length (default 60)")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(may be repeated)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    return parser


def main(argv=None):
    """Entry point: parse flags, check, return the exit code."""
    args = build_parser().parse_args(argv)
    if args.min > args.max:
        print("error: --min %d is larger than --max %d"
              % (args.min, args.max), file=sys.stderr)
        return 2
    if args.stdin:
        return run_stdin(args.min, args.max, as_json=args.json)
    if not args.paths:
        print("error: give a file or folder to check, or use --stdin",
              file=sys.stderr)
        return 2
    return run(args.paths, args.min, args.max,
               recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
