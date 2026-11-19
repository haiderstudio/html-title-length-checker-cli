# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the HTML files you point it at, and it never rewrites a file and never changes anything. It writes nothing except the report on standard output (and usage errors on standard error). It never fetches a URL.

It only checks that titles are 30–60 characters long. It never adds a title, never deletes a title, never changes a title, and never runs code found in an HTML file.

If you find a case where the tool rewrites a file, opens a URL, or reports a pass for an HTML file with a missing, empty or out-of-range title, please open an issue describing the exact commands and input. Do not include any real secret in the report.
