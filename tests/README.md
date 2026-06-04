# tests/

## Purpose
All tests for Company Brain. Test structure mirrors the backend module structure.
Every backend file must have a corresponding test file.

## Structure
```
tests/
├── unit/
│   ├── models/        → tests for models/
│   ├── ingestion/     → tests for ingestion/
│   ├── retrieval/     → tests for retrieval/
│   ├── reasoning/     → tests for reasoning/
│   └── graph/         → tests for graph/
└── integration/       → end-to-end tests (real DB, real API)
```

## Rules
- Every file in `backend/` must have a `test_<filename>.py` in the matching `tests/unit/` subdirectory
- Unit tests must NOT hit real databases — use mocks/fakes
- Integration tests live in `tests/integration/` and may use a test database
- Tests must be runnable with `pytest` from the repo root

## Naming Convention
```
backend/ingestion/slack.py → tests/unit/ingestion/test_slack.py
backend/retrieval/scorer.py → tests/unit/retrieval/test_scorer.py
```

## Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Specific module
pytest tests/unit/ingestion/

# With coverage
pytest --cov=backend tests/
```

## Test Template
Every test file should follow this structure:
```python
# Purpose: Tests for ingestion/slack.py
# Tests: normalize_message(), fetch_thread(), handle_reaction()

import pytest
from backend.ingestion.slack import normalize_message

class TestNormalizeMessage:
    def test_basic_message(self): ...
    def test_empty_content(self): ...
    def test_thread_reply(self): ...
    def test_message_with_attachments(self): ...
```
