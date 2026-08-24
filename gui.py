"""
Tkinter front end for yt2mp3.

The download runs on a worker thread and reports back through a queue that the
main thread drains on a timer. Widgets are only ever touched from the main
thread; nothing in _run_download or the progress callback goes near them.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import core

POLL_MS = 100

log = logging.getLogger(__name__)


class App(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=12)
        self.grid(sticky="nsew")

        self.messages: queue.Queue[dict] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.output_dir = Path.home() / "Music"
        self.last_file: Path | None = None

        self._build_widgets()
        self.after(POLL_MS, self._drain_queue)


    def _build_widgets(self) -> None:
        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Paste a URL to start")
        self.folder_var = tk.StringVar(value=str(self.output_dir))
        self.quality_var = tk.StringVar(value=core.DEFAULT_QUALITY)

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="YouTube URL").grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.url_entry = ttk.Entry(self, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        self.url_entry.focus_set()
        self.url_entry.bind("<Return>", lambda _event: self.on_download())

        self.download_btn = ttk.Button(self, text="Download", command=self.on_download)
        self.download_btn.grid(row=1, column=2, sticky="ew")

        ttk.Label(self, text="Save to").grid(row=2, column=0, sticky="w", pady=(12, 2))

        self.folder_label = ttk.Label(
            self, textvariable=self.folder_var, foreground="#555", anchor="w"
        )
        self.folder_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 8))

        self.change_btn = ttk.Button(self, text="Change…", command=self.on_change_folder)
        self.change_btn.grid(row=3, column=2, sticky="ew")

        ttk.Label(self, text="Quality").grid(row=4, column=0, sticky="w", pady=(12, 2))

        self.quality_combo = ttk.Combobox(
            self,
            textvariable=self.quality_var,
            values=[f"{q} kbps" for q in core.QUALITIES],
            state="readonly",
            width=12,
        )
        self.quality_combo.set(f"{core.DEFAULT_QUALITY} kbps")
        self.quality_combo.grid(row=5, column=0, sticky="w")

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=1.0)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(16, 6))

        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=7, column=0, columnspan=2, sticky="ew")

        self.cancel_btn = ttk.Button(self, text="Cancel", command=self.on_cancel, state="disabled")
        self.cancel_btn.grid(row=7, column=2, sticky="ew")

        self.open_btn = ttk.Button(
            self, text="Open folder", command=self.on_open_folder, state="disabled"
        )
        self.open_btn.grid(row=8, column=2, sticky="ew", pady=(6, 0))


    def selected_quality(self) -> str:
        """The combobox shows "192 kbps"; yt-dlp wants "192"."""
        return self.quality_var.get().split()[0]

    def on_change_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=str(self.output_dir))
        if chosen:
            self.output_dir = Path(chosen)
            self.folder_var.set(chosen)

    def on_open_folder(self) -> None:
        target = self.last_file.parent if self.last_file else self.output_dir
        try:
            os.startfile(target)  # noqa: S606 - Windows only
        except OSError as exc:
            log.warning("couldn't open %s: %s", target, exc)
            self.status_var.set(f"Couldn't open {target}")

    def on_download(self) -> None:
        """Button handler. Must return fast."""
        if self.worker is not None and self.worker.is_alive():
            return  # already busy

        url = self.url_var.get().strip()
        if not url:
            self.status_var.set("Enter a URL first")
            return

        if not core.ffmpeg_available():
            self.status_var.set("Can't find ffmpeg, so audio can't be converted.")
            return

        self.cancel_event.clear()
        self.last_file = None
        self._set_busy(True)
        self.status_var.set("Starting…")

        self.worker = threading.Thread(
            target=self._run_download,
            args=(url, self.output_dir, self.selected_quality()),
            daemon=True,
        )
        self.worker.start()

    def on_cancel(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self.status_var.set("Cancelling…")

    def _run_download(self, url: str, output_dir: Path, quality: str) -> None:
        """Runs on the worker thread. No widget access anywhere in here."""
        def on_progress(update: dict) -> None:
            self.messages.put({"type": "progress", **update})

        try:
            path = core.download(
                url,
                output_dir,
                on_progress=on_progress,
                quality=quality,
                cancel=self.cancel_event,
            )
        except core.Cancelled:
            self.messages.put({"type": "cancelled"})
        except core.DownloadFailed as exc:
            self.messages.put({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            log.exception("unexpected failure downloading %s", url)
            self.messages.put({"type": "error", "message": f"Unexpected: {exc}"})
        else:
            self.messages.put({"type": "done", "path": str(path)})


    def _drain_queue(self) -> None:
        """Runs on the main thread. The only place widgets get updated."""
        try:
            while True:
                msg = self.messages.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        finally:
            self.after(POLL_MS, self._drain_queue)

    def _handle(self, msg: dict) -> None:
        kind = msg["type"]

        if kind == "progress":
            fraction = msg.get("fraction")

            if fraction is None:
                # Unknown size, or ffmpeg working with no measurable progress
                if self.progress["mode"] != "indeterminate":
                    self.progress.configure(mode="indeterminate")
                    self.progress.start(15)
            else:
                if self.progress["mode"] != "determinate":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                self.progress["value"] = fraction

            self.status_var.set(msg.get("label", ""))

        elif kind == "done":
            self.last_file = Path(msg["path"])
            self.status_var.set(f"Saved {self.last_file.name}")
            self.open_btn.configure(state="normal")
            self._set_busy(False)

        elif kind == "cancelled":
            self.status_var.set("Cancelled")
            self._set_busy(False)

        elif kind == "error":
            self.status_var.set(msg["message"])
            self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        """Disable the controls that shouldn't be touched while work is in flight."""
        for widget in (self.url_entry, self.download_btn, self.change_btn):
            widget.configure(state="disabled" if busy else "normal")

        self.quality_combo.configure(state="disabled" if busy else "readonly")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

        if not busy:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress["value"] = 0


def main() -> None:
    log_file = core.setup_logging()
    log.info("yt2mp3 starting, logging to %s", log_file)

    root = tk.Tk()
    root.title("yt2mp3")
    root.minsize(520, 300)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
