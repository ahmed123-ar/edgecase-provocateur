"""Edgecase-Provocateur: educational adversarial testing with Socratic feedback."""

from .core import analyze, analyze_with, provoke
from .hints import HintError
from .models import AnalysisReport, CaseResult
from .report import format_report, format_report_html, print_report

__version__ = "0.2.0"

__all__ = [
    "provoke",
    "analyze",
    "analyze_with",
    "AnalysisReport",
    "CaseResult",
    "HintError",
    "format_report",
    "format_report_html",
    "print_report",
    "__version__",
]
