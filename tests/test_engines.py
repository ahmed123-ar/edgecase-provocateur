import math
import sys

from edgecase_provocateur.engines import variants_for


def test_int_variants():
    v = variants_for(5)
    assert 0 in v and -1 in v and sys.maxsize in v and -sys.maxsize - 1 in v
    assert 5 not in v


def test_bool_is_not_treated_as_int():
    assert variants_for(True) == [False]
    assert variants_for(False) == [True]


def test_float_variants_include_nan_and_inf():
    v = variants_for(2.5)
    assert float("inf") in v
    assert any(isinstance(x, float) and math.isnan(x) for x in v)


def test_unknown_type_returns_no_variants():
    class Thing:
        pass

    assert variants_for(Thing()) == []


def test_variants_are_deterministic():
    assert variants_for(7) == variants_for(7)


from edgecase_provocateur.engines import generate_adversarial_inputs, generate_cases


def test_list_variants_include_empty_none_mixed_duplicates():
    v = variants_for([1, 2])
    assert [] in v
    assert [None] in v
    assert [0, "mixed"] in v
    assert [1, 1, 1] in v


def test_tuple_variants_stay_tuples():
    v = variants_for((1, 2))
    assert () in v
    assert all(isinstance(x, tuple) for x in v)


def test_string_variants_respect_max_length():
    v = variants_for("hi", max_str_len=10)
    assert "" in v and " " in v
    assert "A" * 10 in v
    assert max(len(x) for x in v) == 10


def test_dict_variants_missing_key_and_none_value():
    v = variants_for({"a": 1, "b": 2})
    assert {} in v
    assert {"b": 2} in v
    assert {"a": None, "b": 2} in v


def test_none_variants_exclude_none_itself():
    v = variants_for(None)
    assert None not in v and 0 in v and [] in v


def test_variants_do_not_repeat_original():
    assert [] not in variants_for([])
    assert "" not in variants_for("")


def test_one_argument_changed_at_a_time():
    cases = generate_cases((1, "x"))
    for probe in cases:
        changed = [i for i, (a, b) in enumerate(zip(probe.args, (1, "x"))) if a != b]
        assert changed == [probe.target]


def test_keyword_arguments_are_mutated():
    cases = generate_cases((), {"n": 3})
    assert cases and all(p.target == "n" for p in cases)
    assert any(p.kwargs["n"] == 0 for p in cases)


def test_max_cases_caps_output():
    assert len(generate_cases(([1],) * 10, max_cases=5)) == 5


def test_generation_is_deterministic():
    assert generate_adversarial_inputs([1], "a", 3) == generate_adversarial_inputs([1], "a", 3)


def test_original_arguments_not_modified():
    original = [1, 2, 3]
    generate_cases((original,))
    assert original == [1, 2, 3]


def test_generation_limits_are_validated():
    import pytest

    with pytest.raises(ValueError, match="max_str_len must be a positive integer"):
        variants_for("hello", max_str_len=0)
    with pytest.raises(ValueError, match="max_str_len must be a positive integer"):
        generate_cases(("hello",), max_str_len=1.5)
    with pytest.raises(ValueError, match="max_cases must be a non-negative integer"):
        generate_cases(("hello",), max_cases=-1)
