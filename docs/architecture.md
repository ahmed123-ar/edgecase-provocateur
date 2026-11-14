# Architecture

```
src/edgecase_provocateur/
├── models.py   Probe, CaseResult, AnalysisReport (dataclasses)
├── engines.py  variants_for(), generate_cases(): bounded edge-case generation
├── core.py     analyze(), @provoke: run probes, capture exceptions
├── coach.py    explain(): exception type -> why + Socratic question
├── report.py   format_report(), print_report()
└── __init__.py public API
```

## Data flow

```
example call ──> engines.generate_cases ──> [Probe, ...]
                                              │ (deep-copied args, stdout muted)
                                              ▼
                              core._run_probe: try func(*a, **k)
                                              │
                                  CaseResult(passed / error, line, text)
                                              ▼
                                       AnalysisReport
                                              ▼
                    report.format_report ──> coach.explain per failure ──> text
```

## Design decisions

- **One argument at a time.** Keeps the case count linear and makes each failure attributable
  to a single input. Pairwise/combinatorial generation is future work.
- **Rule registry in the engine.** Each type has a small rule function registered with
  `@_rule(...)`, so adding a type means adding one function.
- **Explicit `analyze()` first, decorator second.** The decorator is a convenience; it runs the
  function's probes then the real call. Probe failures never alter the real call.
- **Line attribution.** The reported line is the deepest traceback frame in the learner's own
  file, not a frame buried in a library call such as `sum`.
- **Re-entrancy guard.** A `ContextVar` stops a recursive `@provoke` function from starting an
  analysis inside an analysis.
- **Deep-copied probes.** So a function that mutates its argument cannot corrupt the caller's data.
- **Coach gives questions, not patches.** The learner decides the intended behaviour.
- **No dependencies, Python 3.9+.**

## Team ownership

| Area | Modules |
|---|---|
| Input engine | `engines.py`, `tests/test_engines.py` |
| Core execution | `core.py`, `tests/test_core.py`, `tests/test_decorator_output.py` |
| Coach and report | `coach.py`, `report.py`, `tests/test_coach.py`, `tests/test_report.py` |
| Integration and release | `models.py`, `__init__.py`, CI, docs, packaging |
