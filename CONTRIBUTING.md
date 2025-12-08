# Contributing to MT Oil

Thank you for your interest in contributing to the MT Oil project! We welcome contributions from the community.

## Development Workflow

1.  **Fork and Clone**: Fork the repository and clone it locally.
2.  **Environment Setup**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .[dev]
    pre-commit install
    ```
3.  **Branching**: Create a new branch for your feature or bugfix (e.g., `feat/add-decline-curve`, `fix/api-error`).
4.  **Coding Standards**:
    - Use **Black** for formatting.
    - Use **Ruff** for linting.
    - Ensure all public functions have docstrings.
    - Add type hints to function signatures.
5.  **Testing**:
    - Run tests with `pytest`.
    - Ensure all new code is covered by tests.
    - Run `pre-commit run --all-files` before committing.
6.  **Committing**:
    - Use **Semantic Commit Messages**:
        - `feat:` for new features.
        - `fix:` for bug fixes.
        - `docs:` for documentation changes.
        - `style:` for formatting changes.
        - `refactor:` for code refactoring.
        - `test:` for adding missing tests.
        - `chore:` for maintenance tasks.
7.  **Pull Request**: Submit a Pull Request to the `dev` branch.

## Project Structure

- `src/mt_oil/`: Source code package.
- `tests/`: Pytest suite.
- `.github/`: CI/CD configurations.

## Reporting Issues

Please use the GitHub Issues tracker to report bugs or request features. Include detailed information to help us reproduce the issue.
