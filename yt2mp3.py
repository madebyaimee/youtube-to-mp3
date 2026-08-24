"""
Downloads YouTube URLs as .mp3 files, one after another until you quit.
"""

from pathlib import Path

import core

DEFAULT_OUTPUT_DIR = Path.home() / "Music"


def pause() -> None:
    """Hold the window open so a parting message can actually be read.
    """
    try:
        input("Press Enter to close...")
    except (KeyboardInterrupt, EOFError):
        pass


def ask_output_dir(default: Path) -> Path:
    """Ask where to save, offering the last folder used as the default."""
    answer = input(f"Save to [{default}]: ").strip().strip('"')

    if not answer:
        return default

    return Path(answer).expanduser()


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
            path = core.download(url, output_dir)
            print(f"File saved to: {path}")

        except core.DownloadFailed as exc:
            print(exc)
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
