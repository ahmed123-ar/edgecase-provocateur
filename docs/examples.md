# Example use cases

## 1. A student checks homework before submitting

```python
from edgecase_provocateur import provoke

@provoke
def average(scores):
    return sum(scores) / len(scores)

average([80, 90])
```
The report shows `scores = []` raising `ZeroDivisionError` and `[None]`/mixed lists raising
`TypeError`, each with a question such as *"How can you check the denominator before dividing?"*

## 2. An instructor demonstrates why boundary testing matters

Use `analyze()` in a lecture notebook and show `report.failures` alongside the function.
Because generation is deterministic, the output is identical every time.

```python
from edgecase_provocateur import analyze, print_report
print_report(analyze(average, [80, 90]), limit=3)
```

## 3. A TA or beginner QA tester gets starter test ideas

Each failing `CaseResult.changed` (e.g. `scores = []`) is a ready-made case to turn into a real pytest test:

```python
import pytest
def test_average_empty():
    with pytest.raises(ValueError):
        average([])      # after you decide empty input should raise ValueError
```

## 4. Keyword arguments and strings

```python
def repeat(text, times=2):
    return text * times

print_report(analyze(repeat, "ab", times=3))
```

## 5. Quiet programmatic use

```python
@provoke(show=False)
def f(x): return 10 / x
f(5)
print(f.last_report.failures[0].error_type)   # ZeroDivisionError
```

## Reading a report

1. **Edge case**: which argument was changed and to what.
2. **Where**: the line in *your* function that raised.
3. **Why**: the violated assumption, in plain words.
4. **Reflect**: decide the intended behaviour; then fix and re-run.
