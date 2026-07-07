import getclip.core.settings as settings_module


def _redirect_settings_to_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", tmp_path / "settings.json")


def test_load_settings_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    _redirect_settings_to_tmp(monkeypatch, tmp_path)

    result = settings_module.load_settings()
    assert result["recent_folders"] == []
    assert result["history"] == []


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    _redirect_settings_to_tmp(monkeypatch, tmp_path)

    settings_module.save_settings({"recent_folders": ["/a/b"], "history": [], "theme": "darkly"})
    result = settings_module.load_settings()
    assert result["recent_folders"] == ["/a/b"]


def test_add_recent_folder_dedupes_and_orders(tmp_path, monkeypatch):
    _redirect_settings_to_tmp(monkeypatch, tmp_path)

    settings_module.add_recent_folder("/a")
    settings_module.add_recent_folder("/b")
    result = settings_module.add_recent_folder("/a")

    assert result == ["/a", "/b"]


def test_add_recent_folder_caps_at_max(tmp_path, monkeypatch):
    _redirect_settings_to_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(settings_module, "MAX_RECENT_FOLDERS", 2)

    settings_module.add_recent_folder("/a")
    settings_module.add_recent_folder("/b")
    result = settings_module.add_recent_folder("/c")

    assert result == ["/c", "/b"]