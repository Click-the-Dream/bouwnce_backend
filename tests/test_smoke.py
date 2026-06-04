from pathlib import Path


def test_smoke() -> None:
    if not Path("app").exists():
        raise AssertionError("app directory is missing")
