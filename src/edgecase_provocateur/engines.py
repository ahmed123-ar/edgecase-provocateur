"""Edge-case input generation.

The generator is *heuristic and bounded*: it never claims to be exhaustive.
Cases are produced by changing **one argument at a time**, so that a failure
can be traced back to the single input that caused it.

Each supported type has a small *rule*: a function that returns edge-case
values for it. Rules are registered with ``@_rule(...)`` and tried in the
order they appear in this file.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional

from .models import Probe

DEFAULT_MAX_CASES = 200
DEFAULT_MAX_STR_LEN = 256


def _same(a: Any, b: Any) -> bool:
    """True if two values are the same type and equal (NaN-safe)."""
    if type(a) is not type(b):
        return False
    try:
        return bool(a == b) or repr(a) == repr(b)
    except Exception:  # exotic __eq__ implementations
        return False


def _unique(candidates: List[Any], original: Any) -> List[Any]:
    """Drop candidates equal to the original value or to each other."""
    out: List[Any] = []
    for cand in candidates:
        if _same(cand, original):
            continue
        if any(_same(cand, seen) for seen in out):
            continue
        out.append(cand)
    return out


# (predicate, generator) pairs, tried in the order they are registered.
_RULES: List[tuple] = []


def _rule(matches: Callable[[Any], bool]):

    def register(fn):
        _RULES.append((matches, fn))
        return fn

    return register


def variants_for(value: Any, max_str_len: int = DEFAULT_MAX_STR_LEN) -> List[Any]:
    """Return a bounded list of edge-oriented variants for one value.

    Types without a rule (custom classes, ...) return an empty list: probing
    them with unrelated values would just produce noisy, invalid inputs.
    """
    if not isinstance(max_str_len, int) or isinstance(max_str_len, bool) or max_str_len < 1:
        raise ValueError("max_str_len must be a positive integer")
    for matches, generate in _RULES:
        if matches(value):
            return _unique(generate(value, max_str_len), value)
    return []


@_rule(lambda v: isinstance(v, bool))
def _bool_variants(value, max_str_len):
    # bool is a subclass of int, so this rule must stay above the int rule.
    return [not value]


@_rule(lambda v: isinstance(v, int))
def _int_variants(value, max_str_len):
    return [0, 1, -1, sys.maxsize, -sys.maxsize - 1]


@_rule(lambda v: isinstance(v, float))
def _float_variants(value, max_str_len):
    return [0.0, -1.0, 5e-324, 1e308, -1e308, float("inf"), float("-inf"), float("nan")]


@_rule(lambda v: isinstance(v, str))
def _str_variants(value, max_str_len):
    return ["", "a", " ", " \t\n ", "A" * max_str_len, "!@#$%^&*()", "héllo 世界"]


@_rule(lambda v: isinstance(v, (list, tuple)))
def _sequence_variants(value, max_str_len):
    make = type(value) if type(value) in (list, tuple) else list
    first = [value[0]] if len(value) else [0]
    return [
        make([]),
        make([None]),
        make(first),
        make(first * 3),  # duplicates
        make(["edgecase_probe"]),
        make([0, "mixed"]),
    ]


@_rule(lambda v: isinstance(v, (set, frozenset)))
def _set_variants(value, max_str_len):
    make = type(value) if type(value) in (set, frozenset) else set
    return [make(), make([None]), make(["edgecase_probe"])]


@_rule(lambda v: isinstance(v, dict))
def _dict_variants(value, max_str_len):
    cands = [{}, {"probe_key": None}]
    if value:
        first_key = next(iter(value))
        cands.append({k: v for k, v in value.items() if k != first_key})  # missing key
        cands.append({**value, first_key: None})  # None value
    return cands


@_rule(lambda v: v is None)
def _none_variants(value, max_str_len):
    return [0, "", [], {}]


def generate_cases(
    args: tuple,
    kwargs: Optional[Dict[str, Any]] = None,
    max_cases: int = DEFAULT_MAX_CASES,
    max_str_len: int = DEFAULT_MAX_STR_LEN,
) -> List[Probe]:
    """Build probes by changing one positional or keyword argument at a time."""
    if not isinstance(max_cases, int) or isinstance(max_cases, bool) or max_cases < 0:
        raise ValueError("max_cases must be a non-negative integer")
    if not isinstance(max_str_len, int) or isinstance(max_str_len, bool) or max_str_len < 1:
        raise ValueError("max_str_len must be a positive integer")
    kwargs = dict(kwargs or {})
    probes: List[Probe] = []
    for index, value in enumerate(args):
        for cand in variants_for(value, max_str_len):
            mutated = list(args)
            mutated[index] = cand
            probes.append(Probe(tuple(mutated), dict(kwargs), index))
    for name, value in kwargs.items():
        for cand in variants_for(value, max_str_len):
            probes.append(Probe(tuple(args), {**kwargs, name: cand}, name))
    return probes[:max_cases]


def generate_adversarial_inputs(*args: Any) -> List[tuple]:
    """Positional-only convenience: return just the mutated argument tuples."""
    return [p.args for p in generate_cases(args)]
