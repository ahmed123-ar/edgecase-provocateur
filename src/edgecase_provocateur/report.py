"""Human-readable report formatting."""

from __future__ import annotations

import html as _html
import sys
from typing import List, Optional, TextIO

from .coach import explain
from .models import AnalysisReport

_BAR = "=" * 60
_RULE = "-" * 60


def format_report(report: AnalysisReport, limit: Optional[int] = None) -> str:
    """Return the report as text. ``limit`` caps how many failures are shown."""
    lines: List[str] = [_BAR, f"EDGECASE-PROVOCATEUR REPORT: {report.function_name}()", _BAR]
    failures = report.failures
    warnings = report.warnings
    if report.example:
        lines.append(f"Example call (inferred from type hints): {report.example}")
    summary = f"{report.total} edge cases tried, {len(failures)} raised an exception."
    if warnings:
        summary += f" {len(warnings)} passed but returned something suspicious."
    lines.append(summary)

    if not failures:
        lines.append("No exceptions detected in the generated cases.")
        lines.append("This is not proof of correctness; consider adding more tests.")
        lines.extend(_warning_lines(report, warnings, limit))
        return "\n".join(lines)

    shown = failures if limit is None else failures[:limit]
    for failure in shown:
        details = explain(failure.error_type, failure.test_input, failure.line_no, failure.message)
        lines.append(_RULE)
        if failure.changed:
            lines.append(f"Edge case : {failure.changed}")
        lines.append(f"Full call : {report.function_name}({failure.describe_input()})")
        lines.append(f"Exception : {failure.error_type}: {failure.message}")
        if failure.line_no is not None:
            where = f"line {failure.line_no}"
            if failure.line_text:
                where += f"  ->  {failure.line_text}"
            lines.append(f"Where     : {where}")
        lines.append(f"Why       : {details['why']}")
        lines.append(f"Reflect   : {details['reflection']}")
    hidden = len(failures) - len(shown)
    if hidden > 0:
        lines.append(_RULE)
        lines.append(f"... and {hidden} more failure(s) not shown.")
    lines.extend(_warning_lines(report, warnings, limit))
    lines.append(_RULE)
    lines.append("Generated cases are heuristic; a clean run is not proof of correctness.")
    return "\n".join(lines)


def _warning_lines(report: AnalysisReport, warnings, limit: Optional[int]) -> List[str]:
    """Text for probes that did not crash but look suspicious, plus general notes."""
    lines: List[str] = []
    if warnings:
        shown = warnings if limit is None else warnings[:limit]
        lines.append(_RULE)
        lines.append("Warnings (no crash, but worth a look)")
        for w in shown:
            lines.append(f"  {w.changed or w.describe_input()}  ->  {w.warning}")
        if len(warnings) > len(shown):
            lines.append(f"  ... and {len(warnings) - len(shown)} more warning(s) not shown.")
        lines.append("Reflect   : Is each of these what you want, or should the function raise an error or return a clear default?")
    if report.notes:
        lines.append(_RULE)
        lines.append("Notes")
        lines.extend(f"  {note}" for note in report.notes)
    return lines


def print_report(
    report: AnalysisReport, limit: Optional[int] = None, file: Optional[TextIO] = None
) -> None:
    """Print :func:`format_report` output (to ``file`` or stdout)."""
    print(format_report(report, limit), file=file or sys.stdout)


_HTML_STYLE = """<style>
.ecp{font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.5;max-width:980px}
.ecp h4{margin:0 0 .5em;font-size:16px}
.ecp table{border-collapse:collapse;width:100%;margin:.4em 0 .8em}
.ecp th,.ecp td{text-align:left;vertical-align:top;padding:6px 10px;border-bottom:1px solid rgba(128,128,128,.35)}
.ecp th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;opacity:.7}
.ecp code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;background:rgba(128,128,128,.16);padding:1px 5px;border-radius:4px}
.ecp .bad{color:#e5484d;font-weight:600}.ecp .ok{color:#2f9e63;font-weight:600}
.ecp .warn{color:#d9822b;font-weight:600}.ecp .ask{font-style:italic}.ecp .fine{opacity:.7;font-size:12px}
</style>"""


def _e(value) -> str:
    return _html.escape(str(value), quote=True)


def format_report_html(report: AnalysisReport, limit: Optional[int] = None) -> str:
    """Return the report as an HTML fragment (this is what Jupyter shows)."""
    failures = report.failures
    parts: List[str] = [_HTML_STYLE, '<div class="ecp">']
    parts.append(f"<h4>Edgecase-Provocateur report: <code>{_e(report.function_name)}()</code></h4>")
    summary = f"{report.total} edge cases tried, "
    if failures:
        summary += f'<span class="bad">{len(failures)} raised an exception</span>.'
    else:
        summary += '<span class="ok">no exceptions raised</span>.'
    warnings = report.warnings
    if warnings:
        summary += f' <span class="warn">{len(warnings)} passed but returned something suspicious.</span>'
    if report.example:
        parts.append(f"<p>Example call (inferred from type hints): <code>{_e(report.example)}</code></p>")
    parts.append(f"<p>{summary}</p>")

    shown = failures if limit is None else failures[:limit]
    if shown:
        parts.append(
            "<table><tr><th>Edge case</th><th>Exception</th><th>Where</th>"
            "<th>Why</th><th>Reflect</th></tr>"
        )
        for f in shown:
            details = explain(f.error_type, f.test_input, f.line_no, f.message)
            where = ""
            if f.line_no is not None:
                where = f"line {f.line_no}"
                if f.line_text:
                    where += f"<br><code>{_e(f.line_text)}</code>"
            parts.append(
                f"<tr><td><code>{_e(f.changed or f.describe_input())}</code></td>"
                f'<td><span class="bad">{_e(f.error_type)}</span><br>{_e(f.message)}</td>'
                f"<td>{where}</td><td>{_e(details['why'])}</td>"
                f'<td class="ask">{_e(details["reflection"])}</td></tr>'
            )
        parts.append("</table>")
        hidden = len(failures) - len(shown)
        if hidden > 0:
            parts.append(f"<p>... and {hidden} more failure(s) not shown.</p>")
    if warnings:
        shown_w = warnings if limit is None else warnings[:limit]
        parts.append("<table><tr><th>Edge case</th><th>Warning (no crash, but worth a look)</th></tr>")
        for w in shown_w:
            parts.append(
                f"<tr><td><code>{_e(w.changed or w.describe_input())}</code></td>"
                f'<td><span class="warn">{_e(w.warning)}</span></td></tr>'
            )
        parts.append("</table>")
    if report.notes:
        parts.append("<p><b>Notes</b></p><ul>" + "".join(f"<li>{_e(n)}</li>" for n in report.notes) + "</ul>")
    parts.append('<p class="fine">Generated cases are heuristic; a clean run is not proof of correctness.</p>')
    parts.append("</div>")
    return "".join(parts)
