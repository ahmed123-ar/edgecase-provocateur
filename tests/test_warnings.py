from edgecase_provocateur import analyze, format_report, format_report_html


def first_or_none(values):
    return values[0] if values else None


def test_returning_none_for_an_edge_case_is_flagged():
    report = analyze(first_or_none, [5])
    assert report.failures == []
    flagged = {w.changed: w.warning for w in report.warnings}
    assert "values = []" in flagged
    assert "returned None" in flagged["values = []"] and "int" in flagged["values = []"]


def test_nan_result_is_flagged():
    def ratio(a, b):
        return a / b if b else float("nan")

    report = analyze(ratio, 1, 2)
    flagged = {w.changed: w.warning for w in report.warnings}
    assert flagged.get("b = 0") == "returned nan"


def test_infinity_result_is_flagged():
    def scale(x):
        return x * 10

    report = analyze(scale, 1.0)
    assert any("inf" in w.warning for w in report.warnings)


def test_no_none_warning_when_the_example_itself_returns_none():
    def shout(text):
        text.upper()

    assert analyze(shout, "hi").warnings == []


def test_warnings_are_not_counted_as_failures():
    report = analyze(first_or_none, [5])
    assert all(r.passed for r in report.warnings)
    assert len(report.failures) == 0


def test_mutating_the_argument_is_noted():
    report = analyze(lambda xs: xs.sort(), [3, 1, 2])
    assert any("xs was modified" in n and "[3, 1, 2]" in n for n in report.notes)


def test_pure_function_has_no_notes():
    assert analyze(lambda xs: sorted(xs), [3, 1, 2]).notes == []


def test_mutating_a_keyword_argument_is_noted():
    def add_item(items=None, extra=None):
        extra.append(1)

    report = analyze(add_item, items=[1], extra=[2])
    assert any("extra was modified" in n for n in report.notes)


def test_failing_example_call_is_noted():
    def first(values):
        return values[0]

    report = analyze(first, [])
    assert any("example call itself raised IndexError" in n for n in report.notes)


def test_text_report_lists_warnings_and_notes():
    text = format_report(analyze(first_or_none, [5]))
    assert "Warnings (no crash, but worth a look)" in text
    assert "values = []  ->  returned None" in text
    assert "1 passed but returned something suspicious" in text or "suspicious" in text
    assert "No exceptions detected" in text  # still says no crash


def test_text_report_unchanged_for_plain_failures():
    def first_plus_one(values):
        return values[0] + 1

    text = format_report(analyze(first_plus_one, [1]))
    assert "Warnings" not in text and "suspicious" not in text


def test_html_report_lists_warnings_and_notes():
    html = format_report_html(analyze(lambda xs: xs.sort(), [3, 1, 2]))
    assert "Notes" in html and "xs was modified" in html
    html = format_report_html(analyze(first_or_none, [5]))
    assert "worth a look" in html and "returned None" in html
