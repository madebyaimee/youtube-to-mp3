"""
Downloads YouTube URLs as .mp3 files, one after another until you quit.
"""

from pathlib import Path

import yt_dlp

import core

DEFAULT_OUTPUT_DIR = Path.home() / "Music"


def pause() -> None:
    """Hold the window open so a parting message can actually be read.

    Double-clicked, this console disappears the moment the process ends.
    """
    try:
        input("Press Enter to close...")
    except (KeyboardInterrupt, EOFError):
        pass


def build_opts(output_dir: Path) -> dict:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'windowsfilenames': True,
        'quiet': False,
        'no_warnings': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    location = core.ffmpeg_location()
    if location is not None:
        ydl_opts['ffmpeg_location'] = location

    return ydl_opts


def ask_output_dir(default: Path) -> Path:
    """Ask where to save, offering the last folder used as the default."""
    answer = input(f"Save to [{default}]: ").strip().strip('"')

    if not answer:
        return default

    return Path(answer).expanduser()


def download(url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with yt_dlp.YoutubeDL(build_opts(output_dir)) as ydl:
        info = ydl.extract_info(url, download=True)

    downloads = info.get('requested_downloads') if info else None
    if downloads:
        print(f"File saved to: {downloads[0]['filepath']}")
    else:
        print(f"Done. Look in {output_dir}")


def main():
    if core.ffmpeg_available() is False:
        print("ffmpeg isn't installed on your system, to install it run 'winget install ffmpeg' then restart your terminal.")
        pause()
        return

    output_dir = DEFAULT_OUTPUT_DIR

    while True:
        try:
            url = input("\nEnter the youtube URL to download [q to quit]: ").strip()

            if url.lower() == 'q':
                print("See you next time babes xo")
                return

            if not url:
                continue

            output_dir = ask_output_dir(output_dir)
            download(url, output_dir)

        except yt_dlp.utils.DownloadError:
            print("This video might be private or geo-blocked so you can't download :(")
        except (KeyboardInterrupt, EOFError):
            print("\nSee you next time babes xo")
            return
        except OSError as exc:
            print(f"Couldn't write to that folder: {exc}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nSomething went wrong: {exc}")
        pause()
