"""End-to-end check of the find_max_difference scenario from the project plan."""

from edgecase_provocateur import analyze


def find_max_difference(numbers):
    largest = numbers[0]
    smallest = numbers[0]
    for num in numbers:
        if num > largest:
            largest = num
        if num < smallest:
            smallest = num
    return largest - smallest


def test_blueprint_scenario():
    report = analyze(find_max_difference, [1, 2, 3])
    by_label = {r.changed: r for r in report.results}
    assert by_label["numbers = []"].error_type == "IndexError"
    assert by_label["numbers = [None]"].error_type == "TypeError"
    assert by_label["numbers = ['edgecase_probe']"].error_type == "TypeError"
    assert by_label["numbers = [1, 1, 1]"].passed
    assert by_label["numbers = []"].line_text == "largest = numbers[0]"
