from getclip.core.url_utils import detect_source_type, SourceType, SOURCE_HINTS


def test_detects_youtube_watch_url():
    assert detect_source_type("https://www.youtube.com/watch?v=abc123") == SourceType.YOUTUBE


def test_detects_youtube_short_url():
    assert detect_source_type("https://youtu.be/abc123") == SourceType.YOUTUBE


def test_detects_twitch_clip():
    assert detect_source_type("https://clips.twitch.tv/SomeClipName") == SourceType.TWITCH_CLIP


def test_detects_twitch_vod():
    assert detect_source_type("https://www.twitch.tv/videos/123456789") == SourceType.TWITCH_VOD


def test_detects_twitch_channel_link_as_live():
    assert detect_source_type("https://www.twitch.tv/somechannel") == SourceType.TWITCH_LIVE


def test_unknown_url():
    assert detect_source_type("https://example.com/video") == SourceType.UNKNOWN


def test_empty_url():
    assert detect_source_type("") == SourceType.UNKNOWN


def test_every_source_type_has_a_hint():
    for source in SourceType:
        assert source in SOURCE_HINTS