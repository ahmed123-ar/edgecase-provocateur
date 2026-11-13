"""Edgecase-Provocateur: educational adversarial testing with Socratic feedback."""

from .core import analyze, provoke
from .models import AnalysisReport, CaseResult
from .report import format_report, print_report

__version__ = "0.1.0"

__all__ = [
    "provoke",
    "analyze",
    "AnalysisReport",
    "CaseResult",
    "format_report",
    "print_report",
    "__version__",
]
