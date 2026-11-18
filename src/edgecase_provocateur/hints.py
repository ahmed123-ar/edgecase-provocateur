"""Build an example call from a function's type hints (used by ``analyze(f)``)."""

from __future__ import annotations

import collections.abc as cabc
import inspect
import typing
from typing import Any, Callable, Dict, List, Tuple

_NONE_TYPE = type(None)


class HintError(ValueError):
    """Raised when an example call cannot be inferred from the type hints."""


def _is_union(origin: Any) -> bool:
    if origin is typing.Union:
        return True
    union_type = getattr(__import__("types"), "UnionType", None)
    return union_type is not None and origin is union_type


def _sample(tp: Any) -> Tuple[Any, bool]:
    """Return (sample value, is_optional) for a type annotation."""
    if tp is Any:
        raise HintError("Any")
    origin = typing.get_origin(tp)
    targs = typing.get_args(tp)

    if _is_union(origin):
        non_none = [a for a in targs if a is not _NONE_TYPE]
        if not non_none:
            raise HintError(repr(tp))
        value, _ = _sample(non_none[0])
        return value, len(non_none) != len(targs)
    if tp is _NONE_TYPE:
        return None, False

    if origin is None:
        if tp is bool:
            return True, False
        simple = {int: 1, float: 1.5, str: "abc", bytes: b"abc", complex: 1j,
                  list: [1, 2, 3], tuple: (1, 2, 3), dict: {"a": 1}, set: {1, 2, 3}, frozenset: frozenset({1, 2, 3})}
        if tp in simple:
            return simple[tp], False
        raise HintError(getattr(tp, "__name__", repr(tp)))

    if origin in (list, cabc.Sequence, cabc.MutableSequence, cabc.Iterable, cabc.Collection):
        return [_sample(targs[0])[0] if targs else 1] * 3 if not targs else _three(targs[0]), False
    if origin is tuple:
        if not targs:
            return (1, 2, 3), False
        if len(targs) == 2 and targs[1] is Ellipsis:
            return tuple(_three(targs[0])), False
        return tuple(_sample(a)[0] for a in targs), False
    if origin in (dict, cabc.Mapping, cabc.MutableMapping):
        if len(targs) == 2:
            return {_sample(targs[0])[0]: _sample(targs[1])[0]}, False
        return {"a": 1}, False
    if origin in (set, cabc.Set, cabc.MutableSet, frozenset):
        items = _three(targs[0]) if targs else [1, 2, 3]
        return (frozenset(items) if origin is frozenset else set(items)), False
    raise HintError(repr(tp))


def _three(tp: Any) -> List[Any]:
    value, _ = _sample(tp)
    if isinstance(value, int) and not isinstance(value, bool):
        return [1, 2, 3]
    if isinstance(value, float):
        return [1.5, 2.5, 3.5]
    if isinstance(value, str):
        return ["a", "b", "c"]
    return [value, value, value]


def infer_example(func: Callable) -> Tuple[tuple, Dict[str, Any], Dict[Any, List[Any]], str]:
    """Return (args, kwargs, extras, description) inferred from ``func``'s signature.

    ``extras`` maps an argument position (int) or keyword (str) to extra edge
    values, e.g. ``None`` for ``Optional[...]`` parameters.
    """
    name = getattr(func, "__name__", "function")
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        raise HintError(f"cannot read the signature of {name}; pass an example call instead")
    try:
        hints = typing.get_type_hints(func)
    except Exception:
        hints = {}

    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    extras: Dict[Any, List[Any]] = {}
    shown: List[str] = []
    for pname, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        optional = False
        if pname in hints:
            try:
                value, optional = _sample(hints[pname])
            except HintError as exc:
                raise HintError(
                    f"cannot build an example for '{pname}' (type {exc}). "
                    f"Pass an example call, e.g. analyze({name}, ...)."
                ) from None
        elif param.default is not param.empty:
            value = param.default
        else:
            raise HintError(
                f"'{pname}' has no type hint or default, so no example can be inferred. "
                f"Add a hint (e.g. {pname}: int) or pass an example call, e.g. analyze({name}, ...)."
            )
        if param.kind is param.POSITIONAL_ONLY:
            key: Any = len(args)
            args.append(value)
            shown.append(repr(value))
        else:
            key = pname
            kwargs[pname] = value
            shown.append(f"{pname}={value!r}")
        if optional:
            extras[key] = [None]
    return tuple(args), kwargs, extras, f"{name}({', '.join(shown)})"
