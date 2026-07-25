"""Run this on Windows, once, before building GetClip.win.spec.

Downloads a static ffmpeg.exe build and places it at assets/win/ffmpeg.exe so
it gets bundled into the .exe (see GetClip.win.spec and
getclip/services/downloader.py:_bundled_ffmpeg_path).
"""
import io
import os
import sys
import urllib.request
import zipfile

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
DEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "win")
DEST_PATH = os.path.join(DEST_DIR, "ffmpeg.exe")


def main():
    if sys.platform != "win32":
        print("This script downloads a Windows ffmpeg.exe build; run it on Windows.")
        sys.exit(1)

    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Downloading {FFMPEG_URL} ...")
    with urllib.request.urlopen(FFMPEG_URL) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    member = next(n for n in archive.namelist() if n.endswith("bin/ffmpeg.exe"))
    print(f"Extracting {member} -> {DEST_PATH}")
    with archive.open(member) as src, open(DEST_PATH, "wb") as dst:
        dst.write(src.read())

    print("Done. Now run: pyinstaller GetClip.win.spec")


if __name__ == "__main__":
    main()
