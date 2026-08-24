# yt2mp3

Paste a YouTube link, get an mp3. One URL in, one file out.

Files come out at 192 kbps by default, tagged with the title and channel, with
the video thumbnail embedded as cover art.

## Just want the app?

Grab `yt2mp3.exe` and double-click it.

Windows will probably show a blue "Windows protected your PC" box the first
time, because the file isn't code-signed. Click **More info** then **Run
anyway**.

The first launch takes a few seconds - the app unpacks itself to a temp folder
before the window appears. After that it's quick.

### Using it

1. Paste a YouTube URL in the top box and hit **Download** (or just press Enter).
2. **Save to** starts as your Music folder. **Change…** picks somewhere else.
3. **Quality** offers 128, 192 or 320 kbps. 192 is the default and is fine for
   almost everything.
4. The bar shows the download, then the conversion to mp3, tagging and cover art.
5. **Cancel** stops it and cleans up any half-finished files.
6. **Open folder** opens wherever the file landed.

## When something goes wrong

The window app has no console, so nothing is ever printed to a screen. It
writes a log instead:

```
%USERPROFILE%\.yt2mp3\yt2mp3.log
```

Most failures show up in the app as a plain sentence:

| What you see | What it means |
| --- | --- |
| That video isn't there… | Deleted, or the link has a typo, or it isn't a YouTube URL |
| That video is private… | Private video |
| That video is for channel members only. | Members-only video |
| That video is age-restricted… | Needs a signed-in account, which this doesn't do |
| That video isn't available in your region. | Region-locked |
| Couldn't find ffmpeg… | Running from source without ffmpeg on your PATH |
| Couldn't download that one… | The catch-all - usually means yt-dlp needs updating |

That last one is the one to watch. YouTube changes things regularly and yt-dlp
gets patched to keep up, but **yt-dlp is frozen into the exe and can't be
upgraded from inside it.** When downloads start failing across the board:

```
uv lock --upgrade-package yt-dlp
uv run pyinstaller yt2mp3.spec
```
