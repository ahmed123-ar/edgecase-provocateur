from edgecase_provocateur import analyze, format_report_html
from edgecase_provocateur.models import AnalysisReport, CaseResult


def first(values):
    return values[0]


def test_report_has_html_repr_for_notebooks():
    report = analyze(first, [1])
    html = report._repr_html_()
    assert isinstance(html, str) and "<table>" in html


def test_html_contains_key_fields():
    html = format_report_html(analyze(first, [1]))
    for part in ("first()", "IndexError", "values = []", "line", "Reflect", "Why"):
        assert part in html


def test_html_escapes_user_data():
    # the TypeError message of this function contains quote characters
    def bad(a):
        return a + 1

    html = format_report_html(analyze(bad, "y"))
    assert "TypeError" in html
    assert "&quot;" in html or "&#x27;" in html
    assert "<script" not in html


def test_html_escapes_function_and_input_text():
    report = AnalysisReport(
        "f<b>", [CaseResult(("<img src=x>",), False, "ValueError", "<bad>", changed="x = '<i>'")]
    )
    html = format_report_html(report)
    assert "<img" not in html and "<bad>" not in html and "<i>" not in html
    assert "&lt;i&gt;" in html


def test_clean_report_html():
    html = format_report_html(analyze(lambda x: x, 1))
    assert "no exceptions raised" in html and "<table>" not in html


def test_html_limit_hides_extra_failures():
    report = AnalysisReport(
        "f", [CaseResult((i,), False, "ValueError", "bad") for i in range(5)]
    )
    assert "3 more failure(s) not shown" in format_report_html(report, limit=2)
