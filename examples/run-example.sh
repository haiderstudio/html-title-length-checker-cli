#!/bin/sh
# Run the checker over each example file and show the result.
# The flagged example fails on purpose, so each run is allowed to fail.
cd "$(dirname "$0")/.."
echo "== examples/clean.html =="
python3 src/html_title_length_checker.py examples/clean.html || true
echo
echo "== examples/flagged.html =="
python3 src/html_title_length_checker.py examples/flagged.html || true
echo
echo "== examples/edge.html =="
python3 src/html_title_length_checker.py examples/edge.html || true
echo
echo "== examples/ : the whole folder =="
python3 src/html_title_length_checker.py examples/ || true
