import pytest

from edgecase_provocateur.coach import explain


@pytest.mark.parametrize(
    "error_type",
    [
        "IndexError", "KeyError", "TypeError", "ZeroDivisionError", "ValueError",
        "AttributeError", "RecursionError", "MemoryError", "OverflowError",
        "StopIteration", "AssertionError", "SomethingCustom",
    ],
)
def test_every_error_gets_why_and_question(error_type):
    out = explain(error_type, ([],), 3, "msg")
    assert out["why"] and out["reflection"].endswith("?")


def test_index_error_mentions_empty():
    assert "empty" in explain("IndexError", ([],), 1, "x")["why"]


def test_none_type_error_gets_none_specific_advice():
    out = explain("TypeError", ([None],), 1, "'>' not supported between 'NoneType' and 'int'")
    assert "None" in out["why"]


def test_plain_type_error_differs_from_none_advice():
    plain = explain("TypeError", (), 1, "unsupported operand")
    assert "contract" in plain["why"]


def test_unknown_error_includes_name_line_and_message():
    out = explain("WeirdError", (), 7, "details")
    assert "WeirdError" in out["why"] and "line 7" in out["why"] and "details" in out["why"]


def test_coach_does_not_hand_out_code_fix():
    out = explain("IndexError", ([],), 1, "x")
    assert "if not" not in out["why"] and "len(" not in out["why"]
