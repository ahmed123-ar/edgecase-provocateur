"""Typed result structures shared by every module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class Probe:
    """One generated test case: a call signature with one value changed.

    ``target`` is the position (``int``) or keyword name (``str``) of the
    argument that was replaced by an edge-case value.
    """

    args: Tuple[Any, ...]
    kwargs: Dict[str, Any] = field(default_factory=dict)
    target: Union[int, str, None] = None


@dataclass
class CaseResult:
    """Outcome of running the function on one probe."""

    test_input: tuple
    passed: bool
    error_type: Optional[str] = None
    message: Optional[str] = None
    line_no: Optional[int] = None
    line_text: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)
    changed: Optional[str] = None  # human-readable "numbers = []"

    def describe_input(self) -> str:
        """Return the call arguments as ``1, [], key=None`` text."""
        parts = [repr(a) for a in self.test_input]
        parts += [f"{k}={v!r}" for k, v in self.kwargs.items()]
        return ", ".join(parts)


@dataclass
class AnalysisReport:
    """All results of one diagnostic pass over a function."""

    function_name: str
    results: List[CaseResult]

    @property
    def failures(self) -> List[CaseResult]:
        return [r for r in self.results if not r.passed]

    @property
    def passes(self) -> List[CaseResult]:
        return [r for r in self.results if r.passed]

    @property
    def total(self) -> int:
        return len(self.results)
