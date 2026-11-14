"""Human-readable report formatting."""

from __future__ import annotations

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
    lines.append(f"{report.total} edge cases tried, {len(failures)} raised an exception.")

    if not failures:
        lines.append("No exceptions detected in the generated cases.")
        lines.append("This is not proof of correctness; consider adding more tests.")
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
    lines.append(_RULE)
    lines.append("Generated cases are heuristic; a clean run is not proof of correctness.")
    return "\n".join(lines)


def print_report(
    report: AnalysisReport, limit: Optional[int] = None, file: Optional[TextIO] = None
) -> None:
    """Print :func:`format_report` output (to ``file`` or stdout)."""
    print(format_report(report, limit), file=file or sys.stdout)
