# uv Migration Design

**Date:** 2026-04-14  
**Status:** Approved

## Goal

Switch plottr to use `uv` for environment management, testing, and running — both locally and in CI. Keep the existing `setuptools` + `versioningit` build backend unchanged.

## Scope

- Consolidate dependencies into `pyproject.toml`
- Remove legacy files (`setup.py`, `requirements.txt`, `test_requirements.txt`)
- Add `uv.lock`
- Update CI workflows to use `uv`
- Update release workflow to use `uv build` + `uv publish`

## Out of Scope

- Changing the build backend (stays `setuptools` + `versioningit`)
- Application source-code changes unrelated to packaging/environment migration
- Test rewrites or behavioral changes beyond the minimal test/CI configuration updates required for the uv migration

---

## Section 1: Dependency Consolidation

### Remove

- `requirements.txt` — duplicates `[project.dependencies]` in `pyproject.toml`
- `test_requirements.txt` — moves to `[dependency-groups]`

### Add to `pyproject.toml`

```toml
[dependency-groups]
test = [
    "qcodes",
    "pytest",
    "pytest-qt",
    "mypy==1.13.0",
    "PyQt6-stubs",
    "pandas-stubs",
]
```

Note: `watchdog` is already in `[project.dependencies]` — not duplicated in test group.

---

## Section 2: Project Files

### Remove

- `setup.py` — legacy setuptools shim, not needed with uv

### Add

- `uv.lock` — generated via `uv lock`, committed to repo for reproducible installs

### Local Dev Workflow

```bash
uv sync --extra pyqt6            # create env + install all deps
uv sync --extra pyqt6 --group test  # include test deps
uv run pytest test/pytest        # run tests
uv run mypy plottr               # type check
uv run plottr-autoplot-ddh5      # run app
uv run plottr-inspectr
uv run plottr-monitr
```

---

## Section 3: CI

### Composite Action (`install-dependencies-and-plottr`)

Slim down to just the sync step — python setup moves to each workflow:

```yaml
- run: uv sync --extra pyqt6 --group test
  shell: bash
```

### Test Workflow (`python-app.yml`)

`setup-uv` with `python-version` lives here (not composite action) so matrix version is accessible:

```yaml
- uses: astral-sh/setup-uv@v6
  with:
    python-version: ${{ matrix.python-version }}
- uses: ./.github/actions/install-dependencies-and-plottr
- run: uv run mypy plottr
- run: uv run pytest test/pytest
```

Drop `actions/setup-python` — uv installs the correct Python automatically.

### Release Workflow (`python-release.yml`)

Replace `python -m build` + twine with:

```yaml
- uses: astral-sh/setup-uv@v6
- run: uv build
- run: uv publish
  env:
    UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

**Secret change required:** Replace `PYPI_USERNAME` + `PYPI_PASSWORD` secrets in GitHub repo settings with a single `PYPI_TOKEN` (PyPI API token).

---

## Testing Plan

1. Run `uv sync --extra pyqt6 --group test` locally — verify env created
2. Run `uv run pytest test/pytest` — all tests pass
3. Run `uv run mypy plottr` — no new errors
4. Push to PR — CI passes on all Python versions (3.11–3.13)
