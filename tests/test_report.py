import io

from edgecase_provocateur import analyze, format_report, print_report
from edgecase_provocateur.models import AnalysisReport, CaseResult


def first(values):
    return values[0]


def test_failure_report_contains_key_fields():
    text = format_report(analyze(first, [1]))
    for part in ("REPORT: first()", "IndexError", "values = []", "Where", "Why", "Reflect", "line"):
        assert part in text


def test_clean_report_warns_not_proof():
    text = format_report(analyze(lambda x: x, 1))
    assert "No exceptions detected" in text and "not proof" in text


def test_empty_results_render():
    assert "0 edge cases" in format_report(AnalysisReport("f", []))


def test_limit_hides_extra_failures():
    report = AnalysisReport(
        "f", [CaseResult((i,), False, "ValueError", "bad") for i in range(5)]
    )
    text = format_report(report, limit=2)
    assert "3 more failure(s) not shown" in text


def test_print_report_writes_to_given_file():
    buf = io.StringIO()
    print_report(analyze(first, [1]), file=buf)
    assert "IndexError" in buf.getvalue()


def test_describe_input_includes_kwargs():
    assert CaseResult((1, []), True, kwargs={"k": None}).describe_input() == "1, [], k=None"


def test_report_counts_split_passes_and_failures():
    report = AnalysisReport(
        "f", [CaseResult((1,), True), CaseResult((2,), False, "ValueError", "bad")]
    )
    assert report.total == 2 and len(report.passes) == 1 and len(report.failures) == 1
