from pathlib import Path


def get_file_extension(file_path: str | Path) -> str:
    """Returns lowercased extension with leading dot"""
    return Path(file_path).suffix.lower()
