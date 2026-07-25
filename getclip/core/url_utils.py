from enum import Enum


class SourceType(Enum):
    YOUTUBE = "youtube"
    TWITCH_CLIP = "twitch_clip"
    TWITCH_VOD = "twitch_vod"
    TWITCH_LIVE = "twitch_live"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    UNKNOWN = "unknown"


def detect_source_type(url: str) -> SourceType:
    url = url.strip().lower()

    if not url:
        return SourceType.UNKNOWN

    if "youtube.com" in url or "youtu.be" in url:
        return SourceType.YOUTUBE

    if "clips.twitch.tv" in url or "/clip/" in url:
        return SourceType.TWITCH_CLIP

    if "twitch.tv" in url and "/videos/" in url:
        return SourceType.TWITCH_VOD

    if "twitch.tv" in url:
        return SourceType.TWITCH_LIVE

    if "tiktok.com" in url:
        return SourceType.TIKTOK

    if "instagram.com" in url:
        return SourceType.INSTAGRAM

    return SourceType.UNKNOWN


SOURCE_HINTS = {
    SourceType.YOUTUBE: "YouTube video detected.",
    SourceType.TWITCH_CLIP: "Twitch clip detected — usually short, trimming optional.",
    SourceType.TWITCH_VOD: "Twitch VOD detected — trimming recommended for long streams.",
    SourceType.TWITCH_LIVE: "Twitch channel link detected — make sure this points to a specific VOD or clip, not a live channel.",
    SourceType.TIKTOK: "TikTok video detected.",
    SourceType.INSTAGRAM: "Instagram post detected — private accounts and some Reels may not be downloadable.",
    SourceType.UNKNOWN: "",
}