# Zenith Tests

Smoke tests are added per Phase, starting with Phase 2 (Main-Channel longform).
Each Mindmap task with a `test_*_smoke.py` reference becomes a file here.

## Layout
- `tests/test_<feature>_smoke.py` -- Smoke tests, one per Mindmap task
- `tests/conftest.py` -- Shared pytest fixtures
- `tests/__init__.py` -- package marker

## Running
pytest tests/
