# PyInstaller spec for the yt2mp3 window app.
#
# Build with:  uv run pyinstaller yt2mp3.spec
#
# This is the one to hand to someone who just wants to save a song. The console
# build (yt2mp3-cli.spec) is the same engine behind a prompt; everything below
# that differs from it is marked GUI ONLY.
#
# Put ffmpeg.exe in a vendor/ folder next to this file first. Use Gyan's
# *essentials* build (~97MB), not the full one (212MB); essentials still has
# libmp3lame and the opus/aac decoders, which is all this needs. See README.

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

VENDOR = Path("vendor")
FFMPEG = VENDOR / "ffmpeg.exe"

if not FFMPEG.exists():
    raise SystemExit(
        f"{FFMPEG} is missing. Copy ffmpeg.exe into vendor/ before building "
        f"(see the build steps in README.md)."
    )

# yt-dlp lazy-loads its extractors, so PyInstaller's static analysis misses them.
# Symptom if this is skipped: "Unsupported URL" in the frozen build only, while
# running from source works fine.
ytdlp_datas, ytdlp_binaries, ytdlp_hiddenimports = collect_all("yt_dlp")

a = Analysis(
    # GUI ONLY: gui.py is the entry point, not yt2mp3.py. It pulls in core.py
    # by import, so core does not need listing.
    ["gui.py"],
    pathex=[],
    binaries=[
        # (source, destination inside the bundle). "." puts it at the root of
        # _MEIPASS, which is what core.ffmpeg_location() returns.
        (str(FFMPEG), "."),
        *ytdlp_binaries,
    ],
    datas=ytdlp_datas,
    hiddenimports=ytdlp_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # GUI ONLY: no excludes. The console spec drops tkinter as dead weight;
    # here tkinter *is* the app, so the excludes list has to stay empty.
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="yt2mp3",
    debug=False,
    strip=False,
    upx=False,          # UPX compression makes antivirus flag it more often
    # GUI ONLY: no console window behind the app. This is what makes it feel
    # like a program rather than a script, and it is also why core.py routes
    # yt-dlp through _YdlLogger - with console=False there is no stdout or
    # stderr at all, and yt-dlp writing to them would take the app down.
    console=False,
    # Leave windowed tracebacks on. If it dies on someone else's machine, a
    # dialog they can screenshot beats a window that vanishes.
    disable_windowed_traceback=False,
    icon=None,          # TODO: point at an .ico once you have one
)

# Notes
# -----
# Build on the target OS. PyInstaller is not a cross-compiler.
#
# There is no console here, so nothing is ever printed. The log file that
# core.setup_logging() opens - ~/.yt2mp3/yt2mp3.log - is the only way to find
# out what went wrong. Ask for that file first when someone reports a problem.
#
# This is a onefile build, so the bootloader unpacks ffmpeg to a temp directory
# on every launch, which costs a few seconds before the window appears. For an
# instant start, add a COLLECT block for a onedir build and zip the folder to
# distribute it instead.
#
# yt-dlp goes stale as YouTube changes things, and users can't upgrade it inside
# a frozen exe. Plan on rebuilding every few months.
