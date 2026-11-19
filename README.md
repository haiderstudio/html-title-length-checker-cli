# html-title-length-checker-cli

Check HTML titles are 30–60 characters long — fail CI when one is not.

[![CI](https://github.com/haiderstudio/html-title-length-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-title-length-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_title_length_checker` reads each HTML file,
measures the stripped text of every `<title>` element,
and reports each missing, empty or out-of-range title
with the file and the line. It exits 1 when any title
fails, so it can fail a CI run. A file whose titles are
all 30–60 characters long exits 0.

- The bounds are inclusive: a title of exactly 30 or
  exactly 60 characters passes.
- The length is measured after leading and trailing
  whitespace is stripped, and after HTML entities are
  decoded — `Tom &amp; Jerry` counts the `&` as one
  character, not five.
- A missing `<title>` is reported on line 1, and an
  empty one on the line its opening tag sits on.
- A file given directly on the command line is always
  checked, whatever its name. A folder is walked for
  files ending in `.html` or `.htm` only, recursively
  by default (`--no-recursive` stops at the top level).
  `.git` folders are never walked, and directory links
  are never followed.
- `--min` and `--max` change the bounds when a project
  wants different ones, for example `--min 10 --max 20`.
- `--json` prints the result as JSON, and `--stdin`
  checks one HTML document read from standard input.

## Who it is for

Every site owner and every developer who ships HTML
pages. A too-short title wastes the search snippet,
and a too-long one gets cut off mid-word in the
results page — both are silent damage to how a page
shows up in search, found only when rankings slip.
This is the gate that keeps titles in the range
search engines show, at the pull request.

## What it does NOT do

- It does not check that a `<title>` exists — that is
  repo #50, html-title-checker-cli. Existence and
  length are different checks on the same tag: a page
  can have a title that is there and still too short
  to say anything.
- It does not check the words in a title, only how
  long it is. A 40-character title that says nothing
  still passes.
- It does not check `<meta name="description">` — that
  is repo #120, html-meta-description-checker-cli.
  The description is a different tag on the same
  pages.
- It does not check Open Graph tags — that is a
  different tag set again.
- It does not rewrite a title for you. It only reports
  the titles that are missing, empty or out of range.
- It never rewrites a file, and it never touches the
  network.

## How this differs

- A fresh search of GitHub on Nov 17, 2026 found 0
  results for `"html-title-length-checker-cli"` and 0
  results for `html title length checker` — the field
  is empty for this job.
- No rival checks the length of `<title>` text in
  local HTML files.

## Install

```sh
git clone https://github.com/haiderstudio/html-title-length-checker-cli.git
cd html-title-length-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_title_length_checker.py page.html
```

A file with a title in range passes:

```sh
$ python3 src/html_title_length_checker.py examples/clean.html
OK — 1 file(s) checked, every title is 30-60 characters long.
```

A file with a title out of range fails, with the file
and line:

```sh
$ python3 src/html_title_length_checker.py examples/flagged.html
FAIL examples/flagged.html: line 5 title is 4 characters long, shorter than the minimum 30
Checked 1 file(s), 1 title problem(s) in 1 file(s).
```

Check a whole folder (`.html` and `.htm` files only):

```sh
$ python3 src/html_title_length_checker.py examples/
FAIL examples/flagged.html: line 5 title is 4 characters long, shorter than the minimum 30
Checked 3 file(s), 1 title problem(s) in 1 file(s).
```

Check one document from standard input:

```sh
$ printf '<!DOCTYPE html>\n<html><head><title>How to Grow Tomatoes at Home in Pots</title></head></html>\n' | python3 src/html_title_length_checker.py --stdin
OK — 1 file(s) checked, every title is 30-60 characters long.
```

Machine-readable output:

```sh
$ python3 src/html_title_length_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 5,
          "reason": "title is 4 characters long, shorter than the minimum 30"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 1
}
```

Exit codes: 0 when every title is in range, 1 when
any title is missing, empty or out of range, or a
file cannot be read, 2 for a usage error (a missing
path, a missing `--min`/`--max` sense, a bad flag, or
no HTML files found).

## Examples

A title that spans lines and holds an entity still
passes — the length is measured after the whitespace
is stripped and the entity is decoded. `examples/edge.html`
has a title split over lines with `&amp;` in it, and
it passes:

```sh
$ python3 src/html_title_length_checker.py examples/edge.html
OK — 1 file(s) checked, every title is 30-60 characters long.
```

A too-long title fails from standard input too — the
title below is 90 characters:

```sh
$ printf '<!DOCTYPE html>\n<html><head><title>The Complete Step-by-Step Guide to Growing Organic Tomatoes at Home in Pots All Year Round</title></head></html>\n' | python3 src/html_title_length_checker.py --stdin
FAIL <stdin>: line 2 title is 90 characters long, longer than the maximum 60
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_title_length_checker.py
```

The tests run the real CLI on throwaway files and
folders, check the bundled examples against their
saved output, and check every command quoted in
this README by running it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool is original work, written for this
repository. It builds on the Python standard
library only (`html.parser`). The idea was
researched against GitHub on Nov 17, 2026 — no
existing tool does this exact job, as noted above
under "How this differs".
