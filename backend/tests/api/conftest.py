import pytest


@pytest.fixture(autouse=True)
def _isolate_db(clean_db: None) -> None:
    """Every test in this package starts from empty tables."""
