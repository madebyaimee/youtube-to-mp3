# yt2mp3

A small command line script that takes a YouTube URL and saves the audio as an
mp3 file.

One URL in, one mp3 out

## Just want the exe?

Grab `yt2mp3-cli.exe` and double-click it. That's everything - no Python, no
yt-dlp, no ffmpeg. It carries its own copy of ffmpeg inside.

Windows will probably show a blue "Windows protected your PC" box the first
time, because the file isn't code-signed. Click **More info** then **Run
anyway**.

Everything below is only for running from source or building the exe yourself.

## What you need

- **Python 3.10 or newer.** Check with `python --version`.
- **yt-dlp**, the Python package. Install with `pip install yt-dlp` (or
  `uv pip install yt-dlp`).
- **ffmpeg**, installed separately and available on your PATH

### Installing ffmpeg

**Windows**

```
winget install Gyan.FFmpeg
```

Then **close and reopen your terminal.**

**macOS**

```
brew install ffmpeg
```

**Linux (Debian/Ubuntu)**

```
sudo apt install ffmpeg
```

Verify it worked by running `ffmpeg -version`. You should get a wall of version
information rather than "command not found".

## Using it

```
python yt2mp3.py
```

It asks for a URL, then where to put the file:

```
Enter the youtube URL to download [q to quit]: https://www.youtube.com/watch?v=EXAMPLE
Save to [C:\Users\you\Music]:
File saved to: C:\Users\you\Music\Some_Video_Title.mp3
```

Press Enter at the "Save to" prompt to accept the folder in brackets. It starts
as your Music folder and then remembers whatever you picked last, so a run of
downloads into the same place is just Enter each time.

It keeps asking until you're done. Type `q` at the URL prompt to quit.


## Building the exe

You need ffmpeg.exe in a `vendor/` folder first. Use the **essentials** build,
not the full one - the full build's ffmpeg.exe is 212MB against 97MB for
essentials, and essentials still has libmp3lame plus the opus/aac decoders,
which is everything this needs.

winget can fetch it without installing anything:

```
winget download --id Gyan.FFmpeg.Essentials --download-directory .\ffdl --skip-license
```

Unzip it and copy `bin\ffmpeg.exe` into `vendor\`. ffprobe is not needed.

Then:

```
uv add --dev pyinstaller
uv run pyinstaller yt2mp3-cli.spec
```

The exe lands in `dist/`. `vendor/` is gitignored - ffmpeg is ~97MB and has
no business in git history.

Build on Windows for Windows - PyInstaller can't cross-compile. And note that
yt-dlp is frozen into the exe, so it can't be upgraded from inside it. When
YouTube changes something and downloads start failing, run
`uv lock --upgrade-package yt-dlp` and rebuild.

## Notes

**"This video might be private or geo-blocked so you can't download"**

This message can also mean:

- The URL has a typo in it, or isn't a YouTube URL at all
- The video is age-restricted
- The video has been deleted
- The video is region-locked and not available where you are
- YouTube changed something and yt-dlp needs updating

It's worth trying this if it does erro:
`pip install --upgrade yt-dlp`. YouTube changes things regularly and yt-dlp
gets patched to keep up