"""Core download logic for yt2mp3.

Both frontends go through here: the console app in yt2mp3.py and the window in
gui.py. Anything yt-dlp-shaped lives in this module.
"""

from __future__ import annotations

import logging
import shutil
import sys
import threading
from pathlib import Path
from typing import Callable

import yt_dlp

log = logging.getLogger(__name__)

DEFAULT_QUALITY = "192"
QUALITIES = ("128", "192", "320")


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


def setup_logging() -> Path:
    """Start writing to the log file and return its path.

    Worth calling before anything else in a windowed build, where this file is
    the only way to find out what went wrong.
    """
    log_dir = Path.home() / ".yt2mp3"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "yt2mp3.log"

    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return log_file


class DownloadFailed(Exception):
    """Raised for anything the user needs to be told about.

    Carries a message already fit for display, so the UI never has to
    interpret a yt-dlp exception itself.
    """


class Cancelled(Exception):
    """Raised when the user stopped the download themselves.

    Kept separate from DownloadFailed so the UI can say "Cancelled" instead of
    presenting a deliberate act as an error.
    """


class _YdlLogger:
    """Send yt-dlp's own output to the log file.

    A windowed build has no stdout or stderr at all - they are None - so
    yt-dlp writing to them would take the whole app down with no visible cause.
    """

    def debug(self, msg: str) -> None:
        # yt-dlp puts real debug lines and ordinary messages through the same
        # method, distinguished only by this prefix.
        if msg.startswith("[debug] "):
            log.debug(msg)
        else:
            log.info(msg)

    def info(self, msg: str) -> None:
        log.info(msg)

    def warning(self, msg: str) -> None:
        log.warning(msg)

    def error(self, msg: str) -> None:
        log.error(msg)


ProgressCallback = Callable[[dict], None]

_POSTPROCESSOR_LABELS = {
    "ExtractAudio": "Converting to mp3",
    "Metadata": "Writing tags",
    "EmbedThumbnail": "Adding cover art",
}


def _mb(byte_count: float) -> str:
    return f"{byte_count / (1024 * 1024):.1f}MB"


def _check_cancelled(cancel: threading.Event | None) -> None:
    """Abort the download if the user asked us to.
    """
    if cancel is not None and cancel.is_set():
        raise yt_dlp.utils.DownloadCancelled("Cancelled")


def _make_progress_hook(on_progress: ProgressCallback | None, cancel: threading.Event | None):
    """Wrap a UI callback into a yt-dlp progress hook.
    """
    def hook(d: dict) -> None:
        _check_cancelled(cancel)

        if on_progress is None:
            return

        status = d.get("status")

        if status == "downloading":
            done = d.get("downloaded_bytes")
            total = d.get("total_bytes") or d.get("total_bytes_estimate")

            if done is not None and total:
                fraction = done / total
                label = f"{_mb(done)} of {_mb(total)}"
            else:
                fraction = None
                label = _mb(done) if done is not None else "Downloading"

            on_progress({"stage": "downloading", "fraction": fraction, "label": label})

        elif status == "finished":
            on_progress({"stage": "downloading", "fraction": 1.0, "label": "Downloaded"})

    return hook


def _make_postprocessor_hook(on_progress: ProgressCallback | None, cancel: threading.Event | None):
    def hook(d: dict) -> None:
        _check_cancelled(cancel)

        if on_progress is None or d.get("status") != "started":
            return

        label = _POSTPROCESSOR_LABELS.get(d.get("postprocessor"))
        if label is not None:
            on_progress({"stage": "converting", "fraction": None, "label": label})

    return hook


def build_opts(
    output_dir: Path,
    on_progress: ProgressCallback | None = None,
    *,
    quality: str = DEFAULT_QUALITY,
    cancel: threading.Event | None = None,
) -> dict:
    """yt-dlp options
    """
    windowed = on_progress is not None

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "restrictfilenames": True,
        "windowsfilenames": True,
        "noplaylist": True,
        "quiet": windowed,
        "no_warnings": True,
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            },
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "progress_hooks": [_make_progress_hook(on_progress, cancel)],
        "postprocessor_hooks": [_make_postprocessor_hook(on_progress, cancel)],
    }

    if windowed:
        opts["logger"] = _YdlLogger()

    location = ffmpeg_location()
    if location is not None:
        opts["ffmpeg_location"] = location

    return opts


def _clean_partials(output_dir: Path, existing_before: set[Path]) -> None:
    """Delete the debris an aborted download leaves behind.
    """
    try:
        created = set(output_dir.iterdir()) - existing_before
    except OSError:
        return

    for path in created:
        if path.suffix.lower() == ".mp3" or not path.is_file():
            continue
        try:
            path.unlink()
        except OSError as exc:
            log.warning("couldn't remove %s: %s", path, exc)


def download(
    url: str,
    output_dir: Path,
    on_progress: ProgressCallback | None = None,
    *,
    quality: str = DEFAULT_QUALITY,
    cancel: threading.Event | None = None,
) -> Path:
    """Download one video's audio as mp3. Returns the path to the finished file.

    Raises Cancelled if the user stopped it, or DownloadFailed with a
    display-ready message on any other failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = build_opts(output_dir, on_progress, quality=quality, cancel=cancel)

    existing_before = set(output_dir.iterdir())

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadCancelled as exc:
        _clean_partials(output_dir, existing_before)
        raise Cancelled from exc
    except yt_dlp.utils.DownloadError as exc:
        if cancel is not None and cancel.is_set():
            _clean_partials(output_dir, existing_before)
            raise Cancelled from exc
        log.error("download failed for %s: %s", url, exc)
        raise DownloadFailed(_explain(exc)) from exc

    downloads = (info or {}).get("requested_downloads")
    if not downloads or "filepath" not in downloads[0]:
        log.error("no filepath in yt-dlp result for %s: %r", url, info)
        raise DownloadFailed(f"Finished, but couldn't tell where the file went. Try {output_dir}.")

    return Path(downloads[0]["filepath"])


def _explain(exc: Exception) -> str:
    """Turn a yt-dlp exception into something worth showing a person.

    The raw text stays in the log file; this is only what reaches the screen.
    """
    text = str(exc).lower()

    if "ffmpeg" in text or "ffprobe" in text:
        return "Couldn't find ffmpeg, so the audio can't be converted to mp3."

    if "private video" in text or "is private" in text:
        return "That video is private, so it can't be downloaded."

    if "members-only" in text or "join this channel" in text:
        return "That video is for channel members only."

    if "age-restricted" in text or "age restricted" in text or "confirm your age" in text:
        return "That video is age-restricted, so it needs a signed-in account."

    if (
        "not available in your country" in text
        or "blocked it in your country" in text
        or "geo-restricted" in text
        or "geo restricted" in text
    ):
        return "That video isn't available in your region."

    if "unavailable" in text or "removed" in text or "not found" in text or "does not exist" in text:
        return "That video isn't there. It may have been deleted, or the link may be wrong."

    return "Couldn't download that one. If it keeps happening, yt-dlp probably needs updating."
