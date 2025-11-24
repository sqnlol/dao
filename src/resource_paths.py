"""Helpers for locating bundled resource files in both source and frozen builds."""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable

_APP_DIR_NAME = "CS2SkinAnalyzer"


@lru_cache(maxsize=1)
def _module_dir() -> Path:
    return Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _bundle_base() -> Path:
    """Return the root directory for resources (handles PyInstaller _MEIPASS)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    mod_dir = _module_dir()
    if mod_dir.name.lower() == "src":
        return mod_dir.parent
    return mod_dir


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


@lru_cache(maxsize=1)
def get_src_dir() -> Path:
    """Return the directory that contains the source tree in all runtimes."""
    base = _bundle_base()
    candidate = base / "src"
    if candidate.exists():
        return candidate
    mod_dir = _module_dir()
    if mod_dir.name.lower() == "src":
        return mod_dir
    return base


def get_asset_path(*relative_parts: str) -> str:
    """Resolve a path inside the packaged src directory (or fallback to module dir)."""
    if not relative_parts:
        raise ValueError("At least one path segment is required")
    rel_path = Path(*relative_parts)
    candidate = get_src_dir() / rel_path
    if candidate.exists():
        return str(candidate)
    fallback = _module_dir() / rel_path
    return str(fallback)


@lru_cache(maxsize=1)
def get_user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    target = Path(base) / _APP_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_data_path(filename: str) -> str:
    path = get_user_data_dir() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def _copy_if_possible(source: Path, dest: Path) -> bool:
    try:
        if source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            return True
    except Exception:
        pass
    return False


def ensure_data_file(filename: str, seed_relative: Iterable[str] | str | None = None) -> str:
    dest = Path(get_data_path(filename))
    if seed_relative and not dest.exists():
        if isinstance(seed_relative, str):
            seed_parts = (seed_relative,)
        else:
            seed_parts = tuple(seed_relative)
        source = Path(get_asset_path(*seed_parts))
        _copy_if_possible(source, dest)
    return str(dest)


def get_writable_suggestions_path() -> str:
    asset_path = Path(get_asset_path("suggestions.txt"))
    if not is_frozen():
        try:
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(asset_path, "a", encoding="utf-8"):
                pass
            return str(asset_path)
        except OSError:
            pass
    dest = Path(get_data_path("suggestions.txt"))
    if not dest.exists():
        copied = _copy_if_possible(asset_path, dest)
        if not copied:
            return str(asset_path)
    return str(dest if dest.exists() else asset_path)
