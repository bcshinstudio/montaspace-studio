"""Application constants and resource paths."""
import sys
from pathlib import Path


PROJECT_FILTER = "MontaSpace Studio Linked (*.mstudio);;MontaSpace Studio Portable (*.mstudiopack)"
VIDEO_FILTER = "Videos (*.mp4)"
VIDEO_EXTENSIONS = {".mp4"}
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PREVIEW_MAX_EDGE = 1600
APP_NAME = "MontaSpace Studio"
APP_VERSION = "0.5.23"
PUBLISHER = "BC Shin Studio"
COPYRIGHT = "© 2026 BC Shin Studio. All rights reserved."
WEBSITE = "https://www.bcshinstudio.com"


def asset_path(relative_path):
    """Locate assets from both source runs and a PyInstaller bundle."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative_path
