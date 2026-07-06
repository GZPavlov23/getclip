from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MediaFormat(Enum):
    MP4 = "mp4"
    MP3 = "mp3"


class Quality(Enum):
    BEST = "Best"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"


@dataclass
class DownloadJob:
    url: str
    output_dir: str
    media_format: MediaFormat = MediaFormat.MP4
    quality: Quality = Quality.BEST
    start_seconds: Optional[int] = None
    end_seconds: Optional[int] = None

    @property
    def is_trimmed(self) -> bool:
        return self.start_seconds is not None and self.end_seconds is not None

@dataclass
class VideoPreview:
    title: str
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]
    
class QueueStatus(Enum):
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    DONE = "Done"
    FAILED = "Failed"


@dataclass
class QueueItem:
    job: DownloadJob
    status: QueueStatus = QueueStatus.PENDING
    label: str = ""
    error: Optional[str] = None