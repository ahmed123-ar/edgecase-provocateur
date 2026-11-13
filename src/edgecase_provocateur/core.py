"""Execution engine: run generated probes and capture exceptions."""

from __future__ import annotations

import contextlib
import contextvars
import copy
import functools
import inspect
import io
import linecache
import traceback
from typing import Any, Callable, Dict, Optional

from .engines import DEFAULT_MAX_CASES, DEFAULT_MAX_STR_LEN, generate_cases
from .models import AnalysisReport, CaseResult, Probe

# True while a diagnostic pass or a decorated call is running. It stops a
# recursive @provoke function from triggering an analysis inside an analysis.
_busy: contextvars.ContextVar = contextvars.ContextVar("edgecase_busy", default=False)


def _safe_copy(value: Any) -> Any:
    """Deep-copy so probes cannot mutate the caller's data (best effort)."""
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


def _label(func: Callable, probe: Probe) -> Optional[str]:
    """Describe which argument was changed, e.g. ``numbers = []``."""
    target = probe.target
    if target is None:
        return None
    if isinstance(target, str):
        return f"{target} = {probe.kwargs[target]!r}"
    value = probe.args[target]
    try:
        names = list(inspect.signature(func).parameters)
        name = names[target] if target < len(names) else f"argument {target}"
    except (TypeError, ValueError):
        name = f"argument {target}"
    return f"{name} = {value!r}"


def _locate(func: Callable, exc: BaseException):
    """Find the failing line, preferring a frame inside the learner's function.

    The deepest traceback frame may be inside a library call (e.g. ``sum``);
    the frame in the learner's own file is usually more useful.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return None, None
    code = getattr(func, "__code__", None)
    own_file = code.co_filename if code else None
    chosen = frames[-1]
    for frame in reversed(frames):
        if own_file and frame.filename == own_file:
            chosen = frame
            break
    text = (chosen.line or linecache.getline(chosen.filename, chosen.lineno)).strip()
    return chosen.lineno, text or None


def _run_probe(func: Callable, probe: Probe) -> CaseResult:
    args = tuple(_safe_copy(a) for a in probe.args)
    kwargs = {k: _safe_copy(v) for k, v in probe.kwargs.items()}
    label = _label(func, probe)
    sink = io.StringIO()  # swallow prints from the probed function
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            func(*args, **kwargs)
    except Exception as exc:  # a diagnostic result, not a crash
        line_no, line_text = _locate(func, exc)
        return CaseResult(
            test_input=probe.args,
            kwargs=probe.kwargs,
            passed=False,
            error_type=type(exc).__name__,
            message=str(exc),
            line_no=line_no,
            line_text=line_text,
            changed=label,
        )
    return CaseResult(test_input=probe.args, kwargs=probe.kwargs, passed=True, changed=label)


def _analyze(
    func: Callable,
    args: tuple,
    kwargs: Dict[str, Any],
    max_cases: int,
    max_str_len: int,
) -> AnalysisReport:
    token = _busy.set(True)
    try:
        probes = generate_cases(args, kwargs, max_cases, max_str_len)
        results = [_run_probe(func, p) for p in probes]
    finally:
        _busy.reset(token)
    name = getattr(func, "__name__", repr(func))
    return AnalysisReport(name, results)


def analyze(func: Callable, *args: Any, **kwargs: Any) -> AnalysisReport:
    """Probe ``func`` with edge cases derived from the example call ``func(*args, **kwargs)``.

    This is the explicit, recommended API. It returns an :class:`AnalysisReport`
    and prints nothing. The function is called many times, so avoid functions
    with irreversible side effects.
    """
    return _analyze(func, args, kwargs, DEFAULT_MAX_CASES, DEFAULT_MAX_STR_LEN)


def provoke(
    func: Optional[Callable] = None,
    *,
    once: bool = True,
    show: bool = True,
    max_cases: int = DEFAULT_MAX_CASES,
    max_str_len: int = DEFAULT_MAX_STR_LEN,
):
    """Decorator that probes a function with edge cases when it is called.

    Works as ``@provoke`` or ``@provoke(once=False)``. On a call, the real
    arguments are used as the example, the probe report is printed, and then
    the function runs normally with the original arguments. Probe failures
    never stop or change the real call.

    Args:
        once: analyze only on the first call (default) instead of every call.
        show: print the report. If False the report is kept on
            ``wrapper.last_report`` only.
        max_cases: upper bound on generated cases.
        max_str_len: length of the "long string" probe.
    """

    def decorate(f: Callable) -> Callable:
        analyzed = False

        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any):
            nonlocal analyzed
            if _busy.get() or (once and analyzed):
                return f(*args, **kwargs)
            analyzed = True
            token = _busy.set(True)
            try:
                # Analyze copies so the real call below sees untouched arguments.
                report = _analyze(
                    f,
                    tuple(_safe_copy(a) for a in args),
                    {k: _safe_copy(v) for k, v in kwargs.items()},
                    max_cases,
                    max_str_len,
                )
                wrapper.last_report = report
                if show:
                    from .report import print_report

                    print_report(report)
                return f(*args, **kwargs)
            finally:
                _busy.reset(token)

        wrapper.last_report = None
        return wrapper

    return decorate(func) if func is not None else decorate