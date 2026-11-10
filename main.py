"""MontaSpace Studio application entry point."""
import sys
from PySide6.QtWidgets import QApplication
from app.window import MontaSpace


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MontaSpace()
    window.show()
    sys.exit(app.exec())
