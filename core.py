"""Core download logic for yt2mp3.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _bundle_dir() -> Path | None:
    """Return the PyInstaller bundle directory, or None if running from source."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return None


def ffmpeg_location() -> str | None:
    """Where yt-dlp should look for ffmpeg.

    Frozen build: the bundle dir, where the spec's binaries entry put ffmpeg.
    Running from source: None, which makes yt-dlp fall back to PATH.
    """
    bundle = _bundle_dir()
    return str(bundle) if bundle is not None else None


def ffmpeg_available() -> bool:
    """Whether we can actually reach an ffmpeg binary.

    ffmpeg_location() is the bundle dir when frozen and None when running from
    source, and shutil.which treats path=None as "search PATH", so the one call
    covers both cases.
    """
    return shutil.which("ffmpeg", path=ffmpeg_location()) is not None