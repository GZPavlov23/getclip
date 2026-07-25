import os
import sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads" / "GetClip")
APP_NAME = "GetClip"
APP_VERSION = "0.1.0"
DEFAULT_FILENAME_TEMPLATE = "{title}"


def resource_path(relative_path: str) -> str:
    """Resolve a path to a bundled asset, whether running from source or a PyInstaller build."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / relative_path)