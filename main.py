"""MontaSpace Studio application entry point."""
import sys

# Configure Qt's FFmpeg backend BEFORE importing any PySide6 modules.
# Deliberately no changes to media players, rendering or project formats.
from app.decoder_policy import configure_decoder
configure_decoder()

from PySide6.QtWidgets import QApplication
from app.window import MontaSpace


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MontaSpace()
    window.show()
    sys.exit(app.exec())
