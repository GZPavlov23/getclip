from getclip.services.downloader import build_outtmpl, _pick_thumbnail_url


def test_build_outtmpl_default_template():
    result = build_outtmpl("/downloads", "{title}")
    assert result == "/downloads/%(title)s.%(ext)s"


def test_build_outtmpl_with_date_and_channel():
    result = build_outtmpl("/downloads", "{date}_{channel}_{title}")
    assert result == "/downloads/%(upload_date)s_%(uploader)s_%(title)s.%(ext)s"


def test_build_outtmpl_falls_back_to_title_when_empty():
    result = build_outtmpl("/downloads", "   ")
    assert result == "/downloads/%(title)s.%(ext)s"


def test_pick_thumbnail_picks_closest_above_target():
    info = {"thumbnails": [
        {"width": 120, "url": "small"},
        {"width": 320, "url": "medium"},
        {"width": 1280, "url": "large"},
    ]}
    assert _pick_thumbnail_url(info, target_width=200) == "medium"


def test_pick_thumbnail_falls_back_to_largest_if_none_big_enough():
    info = {"thumbnails": [
        {"width": 120, "url": "small"},
        {"width": 160, "url": "medium"},
    ]}
    assert _pick_thumbnail_url(info, target_width=999) == "medium"


def test_pick_thumbnail_falls_back_to_plain_thumbnail_key():
    info = {"thumbnail": "fallback_url"}
    assert _pick_thumbnail_url(info, target_width=200) == "fallback_url"