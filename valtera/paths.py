"""Where the repo keeps the App definition, the theme and the Custom Extensions, and where a build writes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
THEME_DIR = ROOT / "theme"
EXT_DIR = ROOT / "extensions"


def workdir(app_name):
    """Where the build writes the generated files for one app name (git-ignored)."""
    return ROOT / ".build" / app_name
