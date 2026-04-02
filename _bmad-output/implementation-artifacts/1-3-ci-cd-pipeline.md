# Story 1.3: CI/CD Pipeline

Status: completed

## Story

As a developer,
I want automated quality gates on every PR,
So that no broken code gets merged.

## Context

GitHub Actions CI/CD pipeline with:
- **Frontend:** pnpm lint → test → build
- **Backend:** ruff check → pytest

## Acceptance Criteria

**Given** a PR is opened
**When** CI pipeline runs
**Then** frontend job runs: lint → test → build
**And** backend job runs: ruff check → pytest
**And** both jobs must pass for merge
**And** failing checks block merge

## Technical Requirements

### CI Workflow Structure

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-test-frontend:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 10.5.2
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
        env:
          CI: true

  lint-and-test-backend:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: |
            backend/pyproject.toml
            backend/uv.lock
      - name: Install dependencies
        run: uv sync
        working-directory: ./backend
      - name: Lint
        run: uv run ruff check .
        working-directory: ./backend
      - name: Test
        run: uv run pytest
        working-directory: ./backend
```

### Required Dependencies

**Frontend (package.json devDependencies):**
```json
{
  "devDependencies": {
    "eslint": "^9.0.0",
    "vitest": "^2.0.0"
  }
}
```

**Backend (pyproject.toml dependency groups):**
```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
  "ruff>=0.8.0",
]

[tool.uv]
package = false
```

### GitHub Actions Requirements

1. **ubuntu-latest** runner
2. **pnpm cache** for faster installs
3. **uv cache** for faster Python installs
4. **parallel jobs** - frontend and backend run concurrently
5. **required status checks** - must pass before merge

## Tasks

- [x] Task 1: Create GitHub Actions workflow file
  - [x] Subtask: Create .github/workflows/ci.yml
  - [x] Subtask: Configure pnpm job
  - [x] Subtask: Configure backend job
- [x] Task 2: Configure ESLint for frontend
  - [x] Subtask: Create eslint.config.js
  - [x] Subtask: Add lint script to root package.json
- [x] Task 3: Configure ruff for backend
  - [x] Subtask: Add ruff config to pyproject.toml
  - [x] Subtask: Add ruff check script to pyproject.toml
- [x] Task 4: Create basic tests
  - [x] Subtask: Create frontend vitest setup in root workspace
  - [x] Subtask: Create backend test_health.py
- [x] Task 5: Configure branch protection rules (README instructions)

## Dev Notes

### Critical Configuration

1. **ESLint flat config** - Use eslint.config.js (ESLint 9+) not .eslintrc
2. **Vitest** - Testing framework (not Jest, which doesn't support ESM properly)
3. **Ruff** - Fast Python linter (10-100x faster than flake8)
4. **pytest-asyncio** - Required for async tests

### Source References

- Architecture: Section 3 - Technology Stack
- Best practices: GitHub Actions caching strategies

## File List

- .github/workflows/ci.yml
- eslint.config.js
- src/tests/test_health.test.tsx
- backend/tests/test_health.py (already created in 1.2)

## Validation Evidence

- The CI command sequence is mirrored by the validated local checks: `pnpm install`, `pnpm test`, `pnpm lint`, `pnpm build`, `cd backend && uv run pytest`, and `cd backend && uv run ruff check .`.
- GitHub Actions configuration diagnostics are clean and the workflow now pins the same pnpm version used locally.

## Review Outcome

- pnpm setup is now explicit in CI instead of relying on implicit package-manager detection.
- The frontend smoke test now exercises a client-side render in `jsdom` rather than a server-render-only assertion.
