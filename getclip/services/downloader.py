import os
from typing import Callable, Optional

import yt_dlp

from getclip.core.models import DownloadJob, MediaFormat, VideoPreview

PLACEHOLDER_MAP = {
    "{title}": "%(title)s",
    "{channel}": "%(uploader)s",
    "{date}": "%(upload_date)s",
}

def send_notification(title: str, message: str) -> None:
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    subprocess.run(["osascript", "-e", script])
    
def build_outtmpl(output_dir: str, template: str) -> str:
    pattern = template.strip() or "{title}"
    for placeholder, ydl_field in PLACEHOLDER_MAP.items():
        pattern = pattern.replace(placeholder, ydl_field)
    return os.path.join(output_dir, f"{pattern}.%(ext)s")

ProgressCallback = Callable[[dict], None]

def fetch_preview(url: str) -> VideoPreview:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return VideoPreview(
        title=info.get("title", "Unknown title"),
        thumbnail_url=_pick_thumbnail_url(info, target_width=200),
        duration_seconds=info.get("duration"),
    )


def _pick_thumbnail_url(info: dict, target_width: int) -> str | None:
    thumbnails = info.get("thumbnails") or []
    sized = [t for t in thumbnails if t.get("width")]

    if not sized:
        return info.get("thumbnail")

    sized.sort(key=lambda t: t["width"])

    for thumb in sized:
        if thumb["width"] >= target_width:
            return thumb["url"]

    return sized[-1]["url"]

def run_download(job: DownloadJob, on_progress: Optional[ProgressCallback] = None) -> str:
    ydl_opts = _build_ydl_options(job, on_progress)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(job.url, download=True)
        filename = ydl.prepare_filename(info)

    if job.media_format == MediaFormat.MP3:
        filename = os.path.splitext(filename)[0] + ".mp3"

    return filename

def _build_ydl_options(job: DownloadJob, on_progress: Optional[ProgressCallback]) -> dict:
    options = {
        "outtmpl": build_outtmpl(job.output_dir, job.filename_template),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if on_progress is not None:
        options["progress_hooks"] = [on_progress]

    if job.media_format == MediaFormat.MP3:
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        options["format"] = _video_format_string(job)
        options["merge_output_format"] = "mp4"

    if job.is_trimmed:
        options["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(job.start_seconds, job.end_seconds)]
        )
        options["force_keyframes_at_cuts"] = True

    return options


def _video_format_string(job: DownloadJob) -> str:
    height_map = {"1080p": 1080, "720p": 720, "480p": 480}
    height = height_map.get(job.quality.value)
    height_filter = f"[height<={height}]" if height is not None else ""

    return (
        f"bestvideo[vcodec^=avc1]{height_filter}+bestaudio[acodec^=mp4a]"
        f"/best[vcodec^=avc1]{height_filter}"
        f"/bestvideo{height_filter}+bestaudio"
        f"/best{height_filter}"
    )

import subprocess


def reveal_in_finder(path: str) -> None:
    subprocess.run(["open", "-R", path])