import json
from pathlib import Path

SETTINGS_DIR = Path.home() / "Library" / "Application Support" / "GetClip"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

MAX_RECENT_FOLDERS = 5
MAX_HISTORY_ITEMS = 200

DEFAULT_SETTINGS = {
    "recent_folders": [],
    "history": [],
    "theme": "darkly",
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)

    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        return {**DEFAULT_SETTINGS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def add_recent_folder(folder: str) -> list[str]:
    settings = load_settings()
    recent = settings.get("recent_folders", [])

    recent = [f for f in recent if f != folder]
    recent.insert(0, folder)
    recent = recent[:MAX_RECENT_FOLDERS]

    settings["recent_folders"] = recent
    save_settings(settings)
    return recent


def add_history_entry(entry: dict) -> list[dict]:
    settings = load_settings()
    history = settings.get("history", [])

    history.insert(0, entry)
    history = history[:MAX_HISTORY_ITEMS]

    settings["history"] = history
    save_settings(settings)
    return history


def clear_history() -> None:
    settings = load_settings()
    settings["history"] = []
    save_settings(settings)