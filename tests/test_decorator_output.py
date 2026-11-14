from edgecase_provocateur import provoke


def test_decorator_prints_report_and_returns_result(capsys):
    @provoke
    def add_one(x):
        return x + 1

    assert add_one(1) == 2
    assert "EDGECASE-PROVOCATEUR REPORT: add_one()" in capsys.readouterr().out


def test_decorator_prints_once_by_default(capsys):
    @provoke
    def f(x):
        return x

    f(1)
    capsys.readouterr()
    f(2)
    assert capsys.readouterr().out == ""


def test_decorator_prints_every_call_when_once_false(capsys):
    @provoke(once=False)
    def f(x):
        return x

    f(1)
    f(2)
    assert capsys.readouterr().out.count("EDGECASE-PROVOCATEUR REPORT") == 2


def test_show_false_stays_silent(capsys):
    @provoke(show=False)
    def f(x):
        return 1 / x

    f(5)
    assert capsys.readouterr().out == ""


def test_recursive_function_does_not_explode(capsys):
    @provoke
    def fact(n):
        return 1 if n <= 1 else n * fact(n - 1)

    assert fact(5) == 120
    assert capsys.readouterr().out.count("REPORT") == 1
