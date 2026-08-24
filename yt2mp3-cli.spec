# PyInstaller spec for the yt2mp3 command line app.
#
# Build with:  uv run pyinstaller yt2mp3-cli.spec
#
# Put ffmpeg.exe in a vendor/ folder next to this file first. Use Gyan's
# *essentials* build (~97MB), not the full one (212MB); essentials still has
# libmp3lame and the opus/aac decoders, which is all this needs. See README.
#
# ffprobe is NOT needed: yt-dlp's get_audio_codec falls back to parsing
# `ffmpeg -i` output when ffprobe is missing, which halves the payload again.
#
# Named yt2mp3-cli rather than yt2mp3 so it can't overwrite yt2mp3.spec, which
# builds the GUI. PyInstaller names generated specs after the target.

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
    ["yt2mp3.py"],
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
    excludes=[
        # The CLI never opens a window, so Tkinter is dead weight here.
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="yt2mp3-cli",
    debug=False,
    strip=False,
    upx=False,          # UPX compression makes antivirus flag it more often
    console=True,       # the app is a prompt; it needs somewhere to read input
    icon=None,          # TODO: point at an .ico once you have one
)

# Notes
# -----
# Build on the target OS. PyInstaller is not a cross-compiler.
#
# This is a onefile build, so the bootloader unpacks ffmpeg to a temp directory
# on every launch, which costs a few seconds. For an instant start, add a
# COLLECT block for a onedir build and zip the folder to distribute it instead.
#
# yt-dlp goes stale as YouTube changes things, and users can't upgrade it inside
# a frozen exe. Plan on rebuilding every few months.
