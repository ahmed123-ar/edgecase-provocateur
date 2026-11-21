"""Execution engine: run generated probes and capture exceptions."""

from __future__ import annotations

import contextlib
import contextvars
import copy
import functools
import inspect
import io
import linecache
import math
import signal
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional

from .engines import DEFAULT_MAX_CASES, DEFAULT_MAX_STR_LEN, generate_cases
from .hints import infer_example
from .models import AnalysisReport, CaseResult, Probe

DEFAULT_TIMEOUT = 2.0  # seconds allowed per probe; None or 0 turns the limit off


class _ProbeTimeout(BaseException):
    """Raised inside a probe that ran too long.

    It derives from BaseException so a bare ``except Exception`` in the learner's
    own code cannot swallow it.
    """


def _can_use_alarm() -> bool:
    """SIGALRM interrupts the running code, but only on Unix and in the main thread."""
    return hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread()


def _call(func: Callable, args: tuple, kwargs: Dict[str, Any], timeout: Optional[float]):
    """Call ``func`` and raise _ProbeTimeout if it runs longer than ``timeout`` seconds."""
    if not timeout or timeout <= 0:
        return func(*args, **kwargs)
    if _can_use_alarm():

        def on_alarm(signum, frame):
            raise _ProbeTimeout()

        previous = signal.signal(signal.SIGALRM, on_alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout)
        try:
            return func(*args, **kwargs)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    # Fallback (Windows, or not the main thread): run in a helper thread and stop
    # waiting for it. Python cannot kill a thread, so a runaway probe keeps running
    # in the background until the program exits.
    box: Dict[str, Any] = {}

    def target():
        try:
            box["value"] = func(*args, **kwargs)
        except BaseException as exc:  # reported back to the caller below
            box["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise _ProbeTimeout()
    if "error" in box:
        raise box["error"]
    return box.get("value")


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


class _Baseline:
    """What the unmodified example call returned (used to spot suspicious results)."""

    def __init__(self, value: Any):
        self.value = value


def _param_names(func: Callable) -> list:
    try:
        return list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return []


def _short(value: Any, limit: int = 60) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _unchanged(before: Any, after: Any) -> bool:
    try:
        return bool(before == after)
    except Exception:  # exotic __eq__: assume nothing changed
        return True


def _is_special_float(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


def _warning_for(value: Any, baseline: Optional[_Baseline]) -> Optional[str]:
    """Flag results that did not crash but probably are not what the learner wants."""
    if baseline is None:
        return None
    if value is None and baseline.value is not None:
        return f"returned None (the example call returned {type(baseline.value).__name__})"
    if _is_special_float(value) and not _is_special_float(baseline.value):
        return f"returned {value!r}"
    return None


def _run_example(func: Callable, args: tuple, kwargs: Dict[str, Any], timeout: Optional[float]):
    """Run the unmodified example once. Returns (baseline or None, notes)."""
    notes: list = []
    before_args = tuple(_safe_copy(a) for a in args)
    before_kwargs = {k: _safe_copy(v) for k, v in kwargs.items()}
    run_args = tuple(_safe_copy(a) for a in args)
    run_kwargs = {k: _safe_copy(v) for k, v in kwargs.items()}
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            value = _call(func, run_args, run_kwargs, timeout)
    except _ProbeTimeout:
        notes.append(f"The example call did not finish within {timeout:g}s, so the warnings below may be incomplete.")
        return None, notes
    except Exception as exc:
        notes.append(
            f"The example call itself raised {type(exc).__name__}: {exc}. "
            "Fix that first; the results below may be unreliable."
        )
        return None, notes
    names = _param_names(func)
    changed = [(names[i] if i < len(names) else f"argument {i}", b, a)
               for i, (b, a) in enumerate(zip(before_args, run_args)) if not _unchanged(b, a)]
    changed += [(k, before_kwargs[k], run_kwargs[k]) for k in kwargs if not _unchanged(before_kwargs[k], run_kwargs[k])]
    for name, before, after in changed:
        notes.append(
            f"{name} was modified by the function (before: {_short(before)}, after: {_short(after)}). "
            "Callers may not expect their data to change."
        )
    return _Baseline(value), notes


def _run_probe(
    func: Callable,
    probe: Probe,
    timeout: Optional[float] = DEFAULT_TIMEOUT,
    baseline: Optional[_Baseline] = None,
) -> CaseResult:
    args = tuple(_safe_copy(a) for a in probe.args)
    kwargs = {k: _safe_copy(v) for k, v in probe.kwargs.items()}
    label = _label(func, probe)
    sink = io.StringIO()  # swallow prints from the probed function
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            value = _call(func, args, kwargs, timeout)
    except _ProbeTimeout as exc:
        line_no, line_text = _locate(func, exc)
        return CaseResult(
            test_input=probe.args,
            kwargs=probe.kwargs,
            passed=False,
            error_type="TimeoutError",
            message=f"did not finish within {timeout:g}s (possible infinite loop or a very large input)",
            line_no=line_no,
            line_text=line_text,
            changed=label,
        )
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
    return CaseResult(
        test_input=probe.args,
        kwargs=probe.kwargs,
        passed=True,
        changed=label,
        warning=_warning_for(value, baseline),
    )


def _analyze(
    func: Callable,
    args: tuple,
    kwargs: Dict[str, Any],
    max_cases: int,
    max_str_len: int,
    timeout: Optional[float] = DEFAULT_TIMEOUT,
    extras: Optional[Dict[Any, List[Any]]] = None,
    example: Optional[str] = None,
) -> AnalysisReport:
    token = _busy.set(True)
    try:
        probes = generate_cases(args, kwargs, max_cases, max_str_len, extras)
        baseline, notes = _run_example(func, args, kwargs, timeout) if probes else (None, [])
        results = [_run_probe(func, p, timeout, baseline) for p in probes]
    finally:
        _busy.reset(token)
    name = getattr(func, "__name__", repr(func))
    return AnalysisReport(name, results, notes, example)


def analyze_with(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    *,
    timeout: Optional[float] = DEFAULT_TIMEOUT,
    max_cases: int = DEFAULT_MAX_CASES,
    max_str_len: int = DEFAULT_MAX_STR_LEN,
) -> AnalysisReport:
    """Like :func:`analyze`, but with options.

    ``args`` and ``kwargs`` are the example call. ``timeout`` is the number of
    seconds each probe may run (``None`` or ``0`` disables the limit).
    """
    return _analyze(func, tuple(args), dict(kwargs or {}), max_cases, max_str_len, timeout)


def analyze(func: Callable, *args: Any, **kwargs: Any) -> AnalysisReport:
    """Probe ``func`` with edge cases derived from the example call ``func(*args, **kwargs)``.

    With no example (``analyze(func)``), one is built from the type hints and
    defaults; ``Optional[...]`` parameters also get a ``None`` probe.

    This is the explicit, recommended API. It returns an :class:`AnalysisReport`
    and prints nothing. The function is called many times, so avoid functions
    with irreversible side effects.
    """
    extras = example = None
    if not args and not kwargs:
        args, kwargs, extras, example = infer_example(func)
    return _analyze(func, args, kwargs, DEFAULT_MAX_CASES, DEFAULT_MAX_STR_LEN, DEFAULT_TIMEOUT, extras, example)


def provoke(
    func: Optional[Callable] = None,
    *,
    once: bool = True,
    show: bool = True,
    max_cases: int = DEFAULT_MAX_CASES,
    max_str_len: int = DEFAULT_MAX_STR_LEN,
    timeout: Optional[float] = DEFAULT_TIMEOUT,
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
        timeout: seconds each probe may run before it is reported as a
            TimeoutError (None or 0 disables the limit). Your real call is
            never time-limited.
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
                    timeout,
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