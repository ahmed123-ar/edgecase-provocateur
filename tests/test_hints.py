import sys
from typing import Dict, List, Optional, Tuple

import pytest

from edgecase_provocateur import HintError, analyze, format_report


def test_simple_types_are_inferred():
    def f(a: int, b: str, c: float) -> str:
        return b * a

    report = analyze(f)
    assert report.example == "f(a=1, b='abc', c=1.5)"
    assert report.total > 0


def test_list_of_int():
    def total(xs: List[int]) -> int:
        return sum(xs) // len(xs)

    report = analyze(total)
    assert report.example == "total(xs=[1, 2, 3])"
    assert any(r.error_type == "ZeroDivisionError" for r in report.failures)


def test_optional_adds_none_probe():
    def double(x: Optional[int]) -> int:
        return x * 2

    report = analyze(double)
    assert any(r.changed == "x = None" and r.error_type == "TypeError" for r in report.failures)


def test_defaults_used_without_hints():
    def greet(name="bob"):
        return name.upper()

    assert analyze(greet).example == "greet(name='bob')"


def test_hinted_and_defaulted_mix():
    def f(a: int, b=10):
        return a / b

    assert analyze(f).example == "f(a=1, b=10)"


def test_missing_hint_raises_helpful_error():
    def f(x):
        return x

    with pytest.raises(HintError) as e:
        analyze(f)
    assert "'x'" in str(e.value) and "analyze(f" in str(e.value)


def test_unsupported_class_raises():
    class Thing:
        pass

    def f(t: Thing):
        return t

    with pytest.raises(HintError):
        analyze(f)


def test_dict_and_tuple():
    def f(d: Dict[str, int], t: Tuple[int, ...]):
        return len(d) + len(t)

    assert analyze(f).example == "f(d={'abc': 1}, t=(1, 2, 3))"


def test_string_annotations():
    def f(x: "int"):
        return x + 1

    assert analyze(f).example == "f(x=1)"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 needs 3.10+")
def test_pep604_optional():
    def f(x: "int | None"):
        return x + 1

    report = analyze(f)
    assert any(r.changed == "x = None" for r in report.failures)


def test_positional_only():
    def f(a: int, /, b: int = 2):
        return a + b

    assert analyze(f).example == "f(1, b=1)"


def test_explicit_example_unchanged_and_no_inferred_line():
    def f(x: int):
        return x + 1

    report = analyze(f, 5)
    assert report.example is None
    assert "inferred" not in format_report(report)


def test_text_report_shows_inferred_example():
    def f(x: Optional[int]):
        return x + 1

    assert "Example call (inferred from type hints): f(x=1)" in format_report(analyze(f))
