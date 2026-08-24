import sys
import subprocess
import yt_dlp


def has_ffmpeg() -> bool:
    try:
        subprocess.run(['ffmpeg', '-h'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    if has_ffmpeg() is False:
        print("ffmpeg isn't installed on your system, to install it run 'winget install ffmpeg' then restart your terminal.")
        sys.exit()

    url = input("Enter the youtube URL to download [q to quit]: ")

    if url.lower() == 'q':
        print("See you next time babes xo")
        sys.exit()

    ydl_opts = {
        'format': 'bestaudio/best',
        'restrictfilenames': True,
        'windowsfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"File saved to: {info['requested_downloads'][0]['filepath']}")
    except yt_dlp.utils.DownloadError:
        print("This video might be private or geo-blocked so you can't download :(")
        sys.exit()


if __name__ == "__main__":
    main()