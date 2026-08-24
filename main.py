import os
import sys
import subprocess
import yt_dlp


def has_ytdlp() -> bool:
    try:
        subprocess.run(['yt-dlp', '-h'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False


def main():
    if has_ytdlp() is False:
        print("yt-dlp isn't installed on your system, to install it run 'winget install yt-dlp'.")
        sys.exit()

    url = input("Enter the youtube URL to download [q to quit]: ")

    if url.lower() == 'q':
        print("See you next time babes xo")
        sys.exit()

    ydl_opts = {
        'format': 'bestaudio/best',
        'restrictfilenames': True,
        'windowsfilenames': True,
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


if __name__ == "__main__":
    main()