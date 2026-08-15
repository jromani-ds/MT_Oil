# Contributing to MT Oil

Thank you for your interest in contributing to the MT Oil project! We welcome contributions from the community.

## Development Workflow

This project follows a `feature → dev → main` branching model. Direct pushes to `dev` and `main` are blocked.

1.  **Clone**: Fork or clone the repository locally.
2.  **Environment Setup**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"
    pre-commit install
    ```
3.  **Branching**: Cut a feature branch from the latest `dev`:
    ```bash
    git checkout dev
    git pull origin dev
    git checkout -b feature/your-descriptive-name
    ```
4.  **Coding Standards**:
    - Use **Black** for formatting.
    - Use **Ruff** for linting.
    - Use **TypeScript / ESLint / Prettier** for frontend code.
    - Terraform code must be formatted (`terraform fmt`) and validated.
    - Ensure all public functions have docstrings.
    - Add type hints to function signatures.
5.  **Testing**:
    - Run backend tests with `pytest tests/`.
    - Run frontend checks with `cd frontend && npm run lint && npm run build`.
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
      - `infra:` for Terraform / deployment changes.
7.  **Pull Request to `dev`**:
    - Open a PR from your feature branch to `dev`.
    - All status checks (tests, lint, Terraform plan) must pass.
    - At least one review is required.
8.  **Promote to `main`**:
    - After merging to `dev`, open a PR from `dev` to `main`.
    - Same checks apply; prod Terraform requires a manual approval.

## Secrets and Security

- **Never commit secrets or service-account keys.**
- Local secrets go in `.env` (ignored by git), not in committed files.
- CI/CD uses Google Cloud Workload Identity Federation — no GCP keys are stored in this repository.
- See [SECURITY.md](SECURITY.md) for the full policy.

## Project Structure

- `src/mt_oil/`: Source code package.
- `tests/`: Pytest suite.
- `.github/`: CI/CD configurations.

## Reporting Issues

Please use the GitHub Issues tracker to report bugs or request features. Include detailed information to help us reproduce the issue.
