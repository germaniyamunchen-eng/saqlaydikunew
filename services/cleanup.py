from pathlib import Path


def remove_file(path: Path | None) -> None:
    if path and path.exists() and path.is_file():
        path.unlink(missing_ok=True)
