# Development Guide

This document outlines the development workflow, tools, and best practices for the Python Utilities repository.

## Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- git

Check your Python version:
```bash
python --version
```

## Initial Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd python
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install project-specific dependencies:
```bash
cd packagemanager-tui
pip install -r requirements.txt
```

## Development Tools

### Testing with pytest

Run all tests:
```bash
pytest
```

Run tests with coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```

Run specific test file:
```bash
pytest tests/test_module.py
```

Run tests with verbose output:
```bash
pytest -v
```

### Code Quality with Ruff

Ruff is a fast Python linter that replaces flake8, isort, pyupgrade, and more.

Check code for issues:
```bash
ruff check .
```

Auto-fix issues where possible:
```bash
ruff check --fix .
```

Format code:
```bash
ruff format .
```

### Type Checking with mypy

Run type checking:
```bash
mypy .
```

### Code Formatting with Black

Format all Python files:
```bash
black .
```

Check formatting without making changes:
```bash
black --check .
```

### Static Analysis

#### Pylint
Run comprehensive code analysis:
```bash
pylint **/*.py
```

Generate report for SonarQube:
```bash
pylint **/*.py --output-format=parseable > pylint-report.txt
```

#### Bandit (Security Analysis)
Scan for security issues:
```bash
bandit -r . -f json -o bandit-report.json
```

#### Vulture (Dead Code Detection)
Find unused code:
```bash
vulture .
```

### SonarQube Analysis

If you have SonarQube set up, run analysis with:
```bash
sonar-scanner
```

Configuration is in `sonar-project.properties`.

## Code Quality Standards

### Code Coverage Target
- Maintain >80% code coverage for all modules
- Critical modules should have >90% coverage
- All public functions must have tests

### Type Hints
- All function parameters and return values must have type hints
- Use `typing` module for complex types
- Example:
```python
from typing import List, Dict, Optional


def process_packages(packages: List[str], options: Optional[Dict[str, str]] = None) -> bool:
    """Process a list of packages."""
    pass
```

### Docstrings
- All public functions, classes, and modules must have docstrings
- Use Google-style docstrings
- Include Args, Returns, and Raises sections where applicable
- Example:
```python
def install_package(package_name: str, version: Optional[str] = None) -> bool:
    """Install a package using the package manager.

    Args:
        package_name: Name of the package to install
        version: Specific version to install (optional)

    Returns:
        True if installation succeeded, False otherwise

    Raises:
        PackageNotFoundError: If package doesn't exist
        InstallationError: If installation fails
    """
    pass
```

### Naming Conventions
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private members: `_leading_underscore`

## Pre-commit Workflow

Before committing code, run these checks:

1. Format code:
```bash
ruff format .
black .
```

2. Fix linting issues:
```bash
ruff check --fix .
```

3. Run type checking:
```bash
mypy .
```

4. Run tests with coverage:
```bash
pytest --cov=. --cov-report=term-missing
```

5. Security scan:
```bash
bandit -r .
```

### Git hooks and the local gate

Install the hooks once per clone (every worktree uses them):

```bash
bash scripts/install-hooks.sh
```

This writes small shims into the clone's shared hooks directory
(`git rev-parse --git-common-dir`/hooks). Each shim runs the checked-out
worktree's `.githooks/<hook>` and refuses the commit or push when that branch has
no such hook (a branch cut before the hooks existed: merge main into it).
`core.hooksPath` must stay unset, and do not run `pre-commit install` (it would
replace the shim). `bash scripts/check-hooks.sh` verifies the wiring. The hooks are:

- `pre-commit`: runs the pre-commit framework's pre-commit hooks (gitleaks,
  typos, actionlint, whitespace). Warns and skips when `pre-commit` is not installed.
- `commit-msg`: runs the conventional-commit check. Same warn-and-skip fallback.
- `pre-push`: requires every commit being pushed to be signed (only commits not
  already on the remote are checked), then runs the full local gate. There is no
  skip switch; `PUSH_GATE` accepts only empty or `full`.

The gate mirrors `.github/workflows/ci.yml` (ruff, pre-commit, fetcher pytest,
bandit, pip-audit, zizmor, the mypy ratchet, actionlint, CI lock freshness). Run it by hand with:

```bash
bash scripts/pre-push-gate.sh
```

With [uv](https://docs.astral.sh/uv/) installed it needs nothing else; tools
run from the same hash locks CI installs (`.github/ci-requirements/`). Without uv, tools found on `PATH` are used and a
missing tool is skipped with a loud `WARN` line. Change the gate and `ci.yml`
together. `bash scripts/check-hooks.sh` verifies the wiring.

### Updating CI tool pins

Every `pip install` in `.github/workflows/` installs a hash lock with
`--require-hashes`. Each install surface has an input
`.github/ci-requirements/<name>.in` (exact tool pins, plus `-r` includes of the
project requirements files) and a generated lock `<name>.lock`. Every lock is
resolved from scratch (no preferences from the old lock) with
`--exclude-newer <EXCLUDE_NEWER>`, a fixed RFC 3339 timestamp set at the top of
`scripts/check-ci-locks-fresh.sh` (the only place it lives). uv ignores every
file uploaded after it, so the resolution is reproducible. To change a pin:

1. Edit the `.in` (or the included project `requirements.txt`), and/or advance
   `EXCLUDE_NEWER` (to a moment in the past) to pick up newer releases, which
   is also how transitive dependencies move.
2. Re-compile every lock with the recipe CI checks:

   ```bash
   bash scripts/check-ci-locks-fresh.sh --write
   ```

3. Commit the `.in`, the script (if the timestamp moved) and the `.lock` files
   together. Never edit a `.lock` by hand.

`bash scripts/check-ci-locks-fresh.sh` (run in the Lint job and by the local
gate) fails when a lock no longer matches a fresh resolution of its `.in`, and
refuses to run with a uv other than the pinned one.
Dependabot does not update these locks (see the comment in
`.github/dependabot.yml`). The uv that runs the check is itself hash-pinned in
`.github/ci-tools/lock-tools.lock`; regenerate it with the command in its header.

## Running the Package Manager TUI

```bash
cd packagemanager-tui
python packagemanager_tui.py
```

## Project Structure

```
python/
├── packagemanager-tui/          # TUI application
│   ├── packagemanager_tui.py    # Main application
│   └── requirements.txt          # App-specific dependencies
├── tests/                        # Test files
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml                # Project metadata and tool config (incl. Ruff)
├── sonar-project.properties      # SonarQube configuration
└── DEVELOPMENT.md                # This file

```

## Continuous Integration

All CI pipelines should run:
1. Ruff linting and formatting checks
2. mypy type checking
3. pytest with coverage reporting
4. Bandit security scanning
5. SonarQube analysis (if configured)

## Troubleshooting

### Import errors
Make sure your virtual environment is activated and dependencies are installed.

### Type checking failures
Ensure all third-party dependencies have type stubs installed (packages starting with `types-`).

### Coverage too low
Run `pytest --cov=. --cov-report=html` to generate an HTML coverage report and identify untested code.

## Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Textual Documentation](https://textual.textualize.io/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
