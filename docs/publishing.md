# Publishing to PyPI (release owner only)

1. Check the name is free: https://pypi.org/project/edgecase-provocateur/ (should 404).
2. Confirm `version` in `pyproject.toml` and `__version__` in `src/edgecase_provocateur/__init__.py` match.
3. Local check in a clean venv:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install build twine
   python -m build
   twine check dist/*
   pip install dist/*.whl && python -c "import edgecase_provocateur as e; print(e.__version__)"
   ```
4. Rehearse on TestPyPI: `twine upload --repository testpypi dist/*`, then
   `pip install -i https://test.pypi.org/simple/ edgecase-provocateur`.
5. Real release, preferably via **trusted publishing** (no token in the repo):
   on pypi.org, go to *Publishing* and add a pending publisher: owner `ahmed123-ar`, repo
   `edgecase-provocateur`, workflow `publish.yml`, environment `pypi`.
   Then create a GitHub release tagged `v0.1.0`; `.github/workflows/publish.yml` uploads it.
   (Alternative: `twine upload dist/*` with an API token. Never commit the token.)
6. Verify: `pip install edgecase-provocateur` in a fresh venv, and that the PyPI page links to the repo.

