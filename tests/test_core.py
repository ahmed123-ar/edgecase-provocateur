from edgecase_provocateur.core import analyze


def first_item(values):
    return values[0]


def test_analysis_captures_index_error():
    report = analyze(first_item, [10])
    assert any(r.error_type == "IndexError" for r in report.failures)


def test_function_name_and_counts():
    def divide(x):
        return 10 / x

    report = analyze(divide, 2)
    assert report.function_name == "divide"
    assert report.total == len(report.results)
    assert any(r.error_type == "ZeroDivisionError" for r in report.failures)


def test_analysis_continues_after_failure():
    report = analyze(first_item, [10])
    assert len(report.passes) >= 1 and len(report.failures) >= 1


def test_clean_function_has_no_failures():
    assert analyze(lambda x: x, 3).failures == []


def test_line_number_and_text_point_into_user_function():
    def uses_sum(values):
        return sum(values)  # library frame is deepest, user line is this one

    report = analyze(uses_sum, [1, 2])
    failure = next(r for r in report.failures if r.error_type == "TypeError")
    assert failure.line_no is not None
    assert "sum(values)" in failure.line_text


def test_changed_label_uses_parameter_name():
    report = analyze(first_item, [10])
    assert report.failures[0].changed == "values = []"


def test_keyword_arguments_supported():
    def f(a, b=1):
        return a / b

    report = analyze(f, 4, b=2)
    assert any(r.changed == "b = 0" and not r.passed for r in report.results)


def test_probes_do_not_mutate_callers_data():
    data = [3, 1, 2]

    def sorter(xs):
        xs.sort()
        xs.append(99)

    analyze(sorter, data)
    assert data == [3, 1, 2]


def test_prints_inside_probed_function_are_suppressed(capsys):
    def noisy(x):
        print("spam")
        return x

    analyze(noisy, 1)
    assert "spam" not in capsys.readouterr().out


import pytest

from edgecase_provocateur.core import provoke


def test_decorator_preserves_metadata_and_result():
    @provoke(show=False)
    def add_one(x):
        """Add one."""
        return x + 1

    assert add_one(1) == 2
    assert add_one.__name__ == "add_one"
    assert add_one.__doc__ == "Add one."


def test_decorator_does_not_swallow_real_exceptions():
    @provoke(show=False)
    def boom(x):
        raise ValueError("real")

    with pytest.raises(ValueError, match="real"):
        boom(1)


def test_decorator_keeps_last_report():
    @provoke(show=False)
    def f(x):
        return 1 / x

    assert f.last_report is None
    f(1)
    assert f.last_report.failures


def test_decorator_analyzes_once_by_default():
    @provoke(show=False)
    def f(x):
        return x

    f(1)
    first = f.last_report
    f(2)
    assert f.last_report is first


def test_decorator_every_call_when_once_false():
    @provoke(once=False, show=False)
    def f(x):
        return x

    f(1)
    first = f.last_report
    f(2)
    assert f.last_report is not first


def test_decorator_original_arguments_untouched():
    @provoke(show=False)
    def pop_last(xs):
        return xs.pop()

    data = [1, 2, 3]
    assert pop_last(data) == 3
    assert data == [1, 2]
