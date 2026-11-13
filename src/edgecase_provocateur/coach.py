"""Socratic feedback: turn an exception into an explanation and a question.

The coach never writes the fix. It names the violated assumption and asks the
learner to decide how the function *should* behave.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def explain(
    error_type: Optional[str],
    failed_input: Any,
    line_no: Optional[int],
    raw_error: Optional[str],
) -> Dict[str, str]:
    """Return ``{"why": ..., "reflection": ...}`` for one failure."""
    location = f" at line {line_no}" if line_no is not None else ""
    raw = raw_error or ""

    if error_type == "IndexError":
        why = (
            "The function tried to use a position in a sequence that does not exist. "
            "Check whether the collection can be empty or shorter than you assumed."
        )
        prompt = "What should the function do when the collection has no items (or too few)?"
    elif error_type == "KeyError":
        why = (
            f"The function looked up the key {raw} in a dictionary that does not "
            "contain it. Check whether every key you read is guaranteed to exist."
        )
        prompt = "Is a missing key an error, or should the function fall back to a default?"
    elif error_type == "TypeError" and "NoneType" in raw:
        why = (
            "A value was None where the function expected a real value. "
            "None often means 'nothing here' and cannot be used in arithmetic, "
            "comparisons, or indexing."
        )
        prompt = "Can this parameter ever be None? Who is responsible for checking?"
    elif error_type == "TypeError":
        why = (
            "An operation received a value of an incompatible type. "
            "Check the input contract and whether values need validating first."
        )
        prompt = "Which input types does this function promise to accept?"
    elif error_type == "ZeroDivisionError":
        why = (
            "A denominator became zero. Consider whether zero is a legal input "
            "and how the function should define its behaviour then."
        )
        prompt = "How can you check the denominator before dividing, and what should be returned?"
    elif error_type == "ValueError":
        why = (
            "The value had the right type but an unsuitable content "
            f"(e.g. converting text to a number, or an empty sequence): {raw}"
        )
        prompt = "Which values are valid for this parameter, and how will you reject the others?"
    elif error_type == "AttributeError":
        why = (
            "The code used an attribute or method that the value does not have. "
            "This often happens when a value is None or a different type than expected."
        )
        prompt = "What type did you assume this value had when you wrote the method call?"
    elif error_type in ("RecursionError", "MemoryError", "OverflowError"):
        why = (
            f"The function hit a resource limit ({error_type}). "
            "Extreme sizes can expose loops or recursion that never settle."
        )
        prompt = "What is the largest input you want to support, and what stops the recursion or growth?"
    elif error_type == "StopIteration":
        why = "The function asked for the next item of an iterator that had none left."
        prompt = "What should happen when there is nothing left to take?"
    elif error_type == "AssertionError":
        why = "An assertion in the code did not hold for this input."
        prompt = "Is this input legal? If so, is the assertion too strict?"
    else:
        why = f"The function raised {error_type}{location}: {raw}"
        prompt = "Which assumption about the input or program state was violated?"
    return {"why": why, "reflection": prompt}
