# Contributing to UCT Benchmark

Thank you for your interest in contributing to the UCT Benchmark project! This document provides guidelines for contributing code, documentation, and bug reports.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Collaborate openly
- Assume good intentions

---

## Getting Started

### Types of Contributions

| Type | Description |
|------|-------------|
| Bug fixes | Fix issues in existing code |
| Features | Add new functionality |
| Documentation | Improve or add docs |
| Tests | Add test coverage |
| Performance | Optimize existing code |

### First Time Contributors

1. Look for issues labeled `good first issue`
2. Comment on the issue to claim it
3. Fork the repository
4. Create a feature branch
5. Make your changes
6. Submit a pull request

---

## Development Setup

### Prerequisites

- Python 3.12+
- Java JDK 17+
- Node.js 18+ (for frontend)
- Git

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/uct-benchmark.git
cd uct-benchmark/UCT-Benchmark-DMR/combined

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install dependencies (including dev tools)
pip install -e ".[dev]"

# 4. Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# 5. Verify setup
make test
```

---

## Code Style

### Python

We use **Ruff** for linting and formatting:

```bash
# Format code
make format
# OR
ruff format .

# Check linting
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Style Guidelines

- **Line length**: 88 characters (Black default)
- **Imports**: Use absolute imports, sorted with isort
- **Type hints**: Encouraged for function signatures
- **Docstrings**: Google style for public functions

```python
def calculate_metrics(
    observations: pd.DataFrame,
    truth: pd.DataFrame,
    threshold: float = 1.0,
) -> dict[str, float]:
    """Calculate evaluation metrics for orbit determination.

    Args:
        observations: DataFrame of observations with ra/dec columns.
        truth: DataFrame of ground truth state vectors.
        threshold: Association distance threshold in km.

    Returns:
        Dictionary containing precision, recall, and F1 score.

    Raises:
        ValueError: If DataFrames are empty or missing required columns.
    """
    ...
```

### TypeScript/React (Frontend)

- Use TypeScript for all new code
- Follow existing component patterns
- Use functional components with hooks

```typescript
interface DatasetCardProps {
  dataset: Dataset;
  onSelect?: (dataset: Dataset) => void;
}

export function DatasetCard({ dataset, onSelect }: DatasetCardProps) {
  // Component implementation
}
```

---

## Testing

### Running Tests

```bash
# Run all tests
make test
# OR
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=uct_benchmark --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names

```python
# tests/test_evaluation.py
import pytest
from uct_benchmark.evaluation import binaryMetrics

class TestBinaryMetrics:
    """Tests for binary classification metrics."""

    def test_perfect_score_returns_1(self):
        """Perfect predictions should return F1 of 1.0."""
        result = binaryMetrics(truth=truth_data, predictions=perfect_predictions)
        assert result["f1_score"] == 1.0

    def test_empty_predictions_raises_error(self):
        """Empty predictions should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            binaryMetrics(truth=truth_data, predictions=[])
```

### Test Coverage Goals

- Aim for >80% coverage on new code
- Critical paths should have >90% coverage
- Don't sacrifice test quality for coverage numbers

---

## Submitting Changes

### Branch Naming

```
feature/add-leaderboard-export
fix/database-connection-leak
docs/update-api-reference
test/add-propagator-tests
```

### Commit Messages

Follow conventional commits format:

```
type(scope): short description

Longer description if needed.

Co-Authored-By: Your Name <email@example.com>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

Examples:
```
feat(api): add batch export endpoint
fix(database): resolve connection pool exhaustion
docs(readme): update installation instructions
test(evaluation): add edge case tests for F1 calculation
```

### Pull Request Process

1. **Create PR** with descriptive title
2. **Fill out template** with:
   - Summary of changes
   - Related issue number
   - Test plan
   - Screenshots (if UI changes)
3. **Request review** from maintainers
4. **Address feedback** promptly
5. **Ensure CI passes** before merge

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New code has tests
- [ ] Documentation updated (if needed)
- [ ] No sensitive data (tokens, passwords) in code
- [ ] Commit messages follow convention

---

## Documentation

### Where to Add Docs

| Content | Location |
|---------|----------|
| User guides | `generated-docs/docs/guides/` |
| Technical reference | `generated-docs/docs/technical/` |
| API docs | Docstrings in code |
| README updates | `README.md` |

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep docs up to date with code changes

### Building Documentation

```bash
cd generated-docs
mkdocs serve  # Local preview at http://localhost:8000
mkdocs build  # Build static site
```

---

## Questions?

- Open a GitHub discussion for general questions
- Tag maintainers in issues if you need guidance
- Check existing issues and PRs for similar topics

---

Thank you for contributing to UCT Benchmark!
