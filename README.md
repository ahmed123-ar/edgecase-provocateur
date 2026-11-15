# edgecase-provocateur

[![tests](https://github.com/ahmed123-ar/edgecase-provocateur/actions/workflows/test.yml/badge.svg)](https://github.com/ahmed123-ar/edgecase-provocateur/actions/workflows/test.yml)

**Probe your Python function with the inputs you forgot, and learn why it broke.**

Edgecase-Provocateur takes a function and an example call, generates a small set of
boundary-oriented inputs (empty lists, `None`, zero, negative numbers, huge values,
odd strings), runs the function on each one, and reports every crash with the failing
input, the exact source line, a plain-English explanation, and a **Socratic question**
that makes you decide how the function *should* behave. It never rewrites your code.

## Motivation

Students tend to test only the "happy path": a few normal lists, positive numbers, short
strings. Code that looks correct then fails on the empty list or the `None` that hidden
tests use. Beginners often don't know *which* cases to try, and a raw traceback explains
*what* happened, not *which assumption was wrong*.

## What's new here

| Existing tool | What it does | Gap for learners |
|---|---|---|
| `pytest` | runs tests you write | you must already know the edge cases |
| Hypothesis | powerful property-based fuzzing | steep learning curve; terse failure output |
| Edgecase-Provocateur | auto-generates beginner-friendly edge cases **and** coaches you through each failure | heuristic, exceptions only (see [limitations](#limitations)) |

The combination is the point: type-aware boundary generation + exception capture +
a readable report + reflection prompts instead of ready-made fixes.

## Install

```bash
pip install edgecase-provocateur
```

Requires Python 3.9+. No dependencies.

## Quick start

```python
from edgecase_provocateur import provoke

@provoke
def find_max_difference(numbers):
    largest = numbers[0]
    smallest = numbers[0]
    for num in numbers:
        if num > largest:
            largest = num
        if num < smallest:
            smallest = num
    return largest - smallest

print(find_max_difference([1, 2, 3]))
```

On the first call the package probes the function and prints:

```
============================================================
EDGECASE-PROVOCATEUR REPORT: find_max_difference()
============================================================
6 edge cases tried, 4 raised an exception.
------------------------------------------------------------
Edge case : numbers = []
Full call : find_max_difference([])
Exception : IndexError: list index out of range
Where     : line 8  ->  largest = numbers[0]
Why       : The function tried to use a position in a sequence that does not exist. ...
Reflect   : What should the function do when the collection has no items (or too few)?
...
```

then runs your real call normally and prints `2`.

### Explicit API (recommended for anything with side effects)

```python
from edgecase_provocateur import analyze, print_report

report = analyze(find_max_difference, [1, 2, 3])   # example call; nothing printed
print_report(report)
print(len(report.failures), "failures")
for failure in report.failures:
    print(failure.changed, failure.error_type, failure.line_no)
```

Keyword arguments work too: `analyze(f, 4, b=2)`.

### Decorator options

```python
@provoke(once=False)        # re-analyze on every call (default: first call only)
@provoke(show=False)        # stay quiet; read f.last_report yourself
@provoke(max_cases=50, max_str_len=64)
```

`max_cases` must be a non-negative integer; `max_str_len` must be a positive integer.

## API

| Name | Description |
|---|---|
| `provoke` | decorator; probes on call, then runs the real call unchanged |
| `analyze(func, *args, **kwargs)` | returns an `AnalysisReport` |
| `AnalysisReport` | `.function_name`, `.results`, `.failures`, `.passes`, `.total` |
| `CaseResult` | `.test_input`, `.kwargs`, `.passed`, `.error_type`, `.message`, `.line_no`, `.line_text`, `.changed` |
| `format_report(report, limit=None)` / `print_report(report)` | render a report |

## What gets generated

One argument is changed at a time, so each failure points at one input.

| Input | Edge cases |
|---|---|
| `int` | 0, 1, -1, `sys.maxsize`, `-sys.maxsize-1` |
| `float` | 0.0, -1.0, tiny, huge, ±inf, NaN |
| `str` | empty, one char, whitespace, long (capped), symbols, Unicode |
| `list` / `tuple` | empty, `[None]`, singleton, duplicates, wrong type, mixed types |
| `dict` | empty, `None` value, missing key |
| `set` | empty, `{None}`, wrong type |
| `bool` | the opposite value |
| `None` | 0, `""`, `[]`, `{}` |

Generation is deterministic and bounded (`max_cases`, default 200).

## Limitations

- **Heuristic, finite.** A clean report is **not** proof of correctness.
- **Exceptions only.** It cannot tell that a function returns a *wrong answer* without a specification.
- **Some probes may be invalid** for your function's contract (e.g. it legitimately only accepts non-empty lists). Treat reports as prompts for reflection.
- **Your function runs many times.** Avoid probing functions that write files, hit the network, or change global state. Output printed by the probed function is suppressed during probing.
- **Not a sandbox.** Catching exceptions is not security isolation; there is no timeout, so an input that makes a function loop forever will hang the run. Never probe untrusted code.
- Probes receive deep copies of your arguments, so your own data is not mutated (best effort for uncopyable objects).

## Development

```bash
git clone https://github.com/ahmed123-ar/edgecase-provocateur
cd edgecase-provocateur
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

More: [architecture](docs/architecture.md) · [examples](docs/examples.md) · [publishing](docs/publishing.md) · [spec](docs/spec.md)

## Team

Ahmed Raza, Hamza Hafeez, Usman Ahmed. CS1302, City University of Hong Kong.

## License

MIT
