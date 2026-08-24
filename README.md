# yt2mp3

A small command line script that takes a YouTube URL and saves the audio as an
mp3 file.

One URL in, one mp3 out

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

It will ask for a URL:

```
Enter the youtube URL to download [q to quit]: https://www.youtube.com/watch?v=EXAMPLE
File saved to: C:\Users\you\Music\Some_Video_Title.mp3
```

The mp3 is saved into whatever folder you were in when you ran the script, so
`cd` to where you want the file first.

Type `q` at the prompt to exit without downloading.


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