"""Application constants and resource paths."""
import sys
from pathlib import Path


PROJECT_FILTER = "MontaSpace Studio Linked (*.mstudio);;MontaSpace Studio Portable (*.mstudiopack)"
VIDEO_FILTER = "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.wmv *.m4v *.mpg *.mpeg)"
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.wmv', '.m4v', '.mpg', '.mpeg'}
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff *.heic *.heif *.avif)"
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff', '.heic', '.heif', '.avif'}
PREVIEW_MAX_EDGE = 1600
APP_NAME = "MontaSpace Studio"
APP_VERSION = "0.6.2"
PUBLISHER = "BC Shin Studio"
COPYRIGHT = "© 2026 BC Shin Studio. All rights reserved."
WEBSITE = "https://www.bcshinstudio.com"


def asset_path(relative_path):
    """Locate assets from both source runs and a PyInstaller bundle."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative_path


def application_icon_path():
    """Choose native icon asset without changing Windows packaging."""
    icon = "MontaSpaceStudio"
    suffix = ".png" if sys.platform == "darwin" else ".ico"
    return asset_path(f"assets/{icon}{suffix}")
