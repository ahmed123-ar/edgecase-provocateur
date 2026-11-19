# Changelog

## 0.2.0
- Jupyter: reports render as an HTML table (`_repr_html_`, `format_report_html`).
- Per-probe timeout (default 2 s); infinite loops are reported as `TimeoutError`. New `analyze_with(...)` and `@provoke(timeout=...)`.
- Warnings for silent problems: `None`/NaN/inf results and arguments modified by the function.
- `analyze(f)` with no example builds one from type hints/defaults; `Optional[...]` adds a `None` probe. New `HintError`.

## 0.1.0
- First release: rule-based edge-case generation, Socratic feedback, `@provoke` and `analyze`.
