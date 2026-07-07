from getclip.services.updater import _is_newer


def test_newer_version_detected():
    assert _is_newer("0.2.0", "0.1.0") is True


def test_same_version_is_not_newer():
    assert _is_newer("0.1.0", "0.1.0") is False


def test_older_version_is_not_newer():
    assert _is_newer("0.1.0", "0.2.0") is False


def test_handles_different_version_lengths():
    assert _is_newer("0.1.1", "0.1") is True