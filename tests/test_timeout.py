import signal
import sys
import time

import pytest

from edgecase_provocateur import analyze_with, core, provoke
from edgecase_provocateur.coach import explain


def countdown(n):
    while n > 0:
        n -= 1
    return n


def test_runaway_input_is_reported_as_timeout_not_a_hang():
    start = time.time()
    report = analyze_with(countdown, (3,), timeout=0.3)
    assert time.time() - start < 10
    timeouts = [r for r in report.failures if r.error_type == "TimeoutError"]
    assert timeouts and "0.3" in timeouts[0].message
    assert timeouts[0].changed == f"n = {sys.maxsize}"


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="needs SIGALRM")
def test_timeout_reports_the_line_that_was_running():
    report = analyze_with(countdown, (3,), timeout=0.3)
    timeout = next(r for r in report.failures if r.error_type == "TimeoutError")
    assert timeout.line_no is not None
    assert "n" in (timeout.line_text or "")


def test_other_probes_still_pass_after_a_timeout():
    report = analyze_with(countdown, (3,), timeout=0.3)
    assert len(report.passes) >= 2


def test_fast_functions_never_time_out():
    report = analyze_with(lambda x: x, (1,), timeout=0.5)
    assert report.failures == []


def test_timeout_none_disables_the_limit():
    report = analyze_with(lambda x: x, (1,), timeout=None)
    assert report.failures == []


def test_timeout_cannot_be_swallowed_by_except_exception():
    def stubborn(n):
        while n > 0:
            try:
                n -= 1
            except Exception:
                pass
        return n

    report = analyze_with(stubborn, (3,), timeout=0.3)
    assert any(r.error_type == "TimeoutError" for r in report.failures)


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="needs SIGALRM")
def test_alarm_handler_is_restored():
    before = signal.getsignal(signal.SIGALRM)
    analyze_with(countdown, (3,), timeout=0.2)
    assert signal.getsignal(signal.SIGALRM) == before


def test_thread_fallback_when_alarm_is_unavailable(monkeypatch):
    monkeypatch.setattr(core, "_can_use_alarm", lambda: False)

    def napper(seconds):
        time.sleep(seconds)

    report = analyze_with(napper, (0,), timeout=0.2)
    assert any(r.error_type == "TimeoutError" and r.changed == "seconds = 1" for r in report.failures)


def test_thread_fallback_still_reports_normal_exceptions(monkeypatch):
    monkeypatch.setattr(core, "_can_use_alarm", lambda: False)
    report = analyze_with(lambda v: v[0], ([1],), timeout=1)
    assert any(r.error_type == "IndexError" for r in report.failures)


def test_decorator_accepts_timeout_and_real_call_is_unlimited():
    @provoke(show=False, timeout=0.3)
    def f(n):
        while n > 0:
            n -= 1
        return "done"

    assert f(2000000) == "done"  # the real call is never time-limited
    assert any(r.error_type == "TimeoutError" for r in f.last_report.failures)


def test_coach_has_a_timeout_explanation():
    out = explain("TimeoutError", (), 3, "slow")
    assert "finish" in out["why"] and out["reflection"].endswith("?")
