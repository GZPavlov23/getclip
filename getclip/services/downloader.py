from typing import Callable, Optional

import yt_dlp

from getclip.core.models import DownloadJob, MediaFormat, VideoPreview


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

def run_download(job: DownloadJob, on_progress: Optional[ProgressCallback] = None) -> None:
    ydl_opts = _build_ydl_options(job, on_progress)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([job.url])


def _build_ydl_options(job: DownloadJob, on_progress: Optional[ProgressCallback]) -> dict:
    options = {
        "outtmpl": f"{job.output_dir}/%(title)s.%(ext)s",
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

    if height is None:
        return "bestvideo+bestaudio/best"

    return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"