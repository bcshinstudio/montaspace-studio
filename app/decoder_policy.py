"""Choose Qt FFmpeg decoding policy before importing Qt multimedia.

User overrides are explicit. Production defaults to software decoding on
Windows because measured five-video loop tests found much lower RAM growth.
"""
import os
import sys

QT_DECODER_ENV = "QT_FFMPEG_DECODING_HW_DEVICE_TYPES"
STUDIO_DECODER_ENV = "MONTASPACE_STUDIO_DECODER"


def configure_decoder(env=None, platform=None):
    """Apply a startup-only decoder policy; return a human-readable mode.

    Called before importing PySide6. Never alter policy during playback.
    Values for MONTASPACE_STUDIO_DECODER: software, hardware, auto.
    auto respects any existing Qt-specific environment override.
    """
    if env is None:
        env = os.environ
    if platform is None:
        platform = sys.platform
    requested = env.get(STUDIO_DECODER_ENV, "").strip().lower()
    if requested == "hardware":
        env.pop(QT_DECODER_ENV, None)
        return "hardware (override)"
    if requested == "software":
        env[QT_DECODER_ENV] = ","
        return "software (override)"
    if requested not in ("", "auto"):
        raise ValueError(
            f"Invalid {STUDIO_DECODER_ENV}={requested!r}; use software, hardware or auto"
        )
    if QT_DECODER_ENV in env:
        return "Qt environment override"
    if platform == "win32":
        env[QT_DECODER_ENV] = ","
        return "software (Windows default)"
    return "Qt platform default"
