"""Clean nonmodal help sheet for MontaSpace Studio mouse and keyboard actions."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)


class ShortcutHelp(QDialog):
    """F1 or Ctrl+H opens a compact, nonblocking reference window."""

    SECTIONS = (
        ("WHITEBOARD", (
            ("Select", "Click media"),
            ("Move", "Left-drag media"),
            ("Resize", "Drag any edge or corner"),
            ("Resize with wheel", "Ctrl + mouse wheel"),
            ("Context menu", "Right-click"),
        )),
        ("PHOTO", (
            ("Crop", "Double-click or Ctrl + double-click"),
            ("Rotate", "Drag rotation handle"),
        )),
        ("VIDEO", (
            ("Play / Pause", "Double-click"),
            ("Playback controls", "Middle-click"),
            ("Crop", "Ctrl + double-click"),
            ("Pan zoomed content", "Shift + left-drag"),
        )),
        ("CROP MODE", (
            ("Apply crop", "Enter"),
            ("Cancel crop", "Esc"),
        )),
        ("PROJECTS & APP", (
            ("New / Open", "Ctrl + N  /  Ctrl + O"),
            ("Save / Save As", "Ctrl + S  /  Ctrl + Shift + S"),
            ("Undo / Redo", "Ctrl + Z  /  Ctrl + Y"),
            ("Duplicate photo", "Ctrl + D"),
            ("Delete selection", "Delete"),
            ("Show/hide window border", "Ctrl + Shift + B"),
            ("Show/hide this help", "Ctrl + H  /  F1"),
        )),
    )

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("MontaSpace Studio · Shortcuts")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.resize(510, 560)
        self.setMinimumWidth(445)
        self.setObjectName("shortcutsHelp")
        self.setStyleSheet("""
        QDialog#shortcutsHelp { background: #f7f9fc; color: #24354b; }
        QFrame#helpCard { background: white; border: 1px solid #e1e7ef; border-radius: 10px; }
        QLabel#helpHeading { font-size: 19px; font-weight: 700; color: #182f48; }
        QLabel#helpLead { color: #61758a; font-size: 12px; }
        QLabel#helpSection { color: #326b97; font-size: 11px; font-weight: 700; }
        QLabel#helpAction { color: #27384b; font-size: 12px; }
        QLabel#helpGesture { color: #425d79; font-size: 12px; }
        QPushButton { background: #e9f0f7; color: #214764; border: 1px solid #d4e2ee;
                      border-radius: 7px; padding: 7px 18px; }
        QPushButton:hover { background: #dceaf5; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 14)
        outer.setSpacing(10)
        title = QLabel("Mouse & keyboard shortcuts")
        title.setObjectName("helpHeading")
        outer.addWidget(title)
        subtitle = QLabel("A quick guide · no shortcuts are displayed on your whiteboard")
        subtitle.setObjectName("helpLead")
        outer.addWidget(subtitle)

        scroll = QScrollArea(self)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        stack = QVBoxLayout(content)
        stack.setContentsMargins(0, 2, 4, 2)
        stack.setSpacing(10)
        for name, actions in self.SECTIONS:
            card = QFrame()
            card.setObjectName("helpCard")
            layout = QGridLayout(card)
            layout.setContentsMargins(13, 11, 13, 12)
            layout.setHorizontalSpacing(18)
            layout.setVerticalSpacing(7)
            section = QLabel(name)
            section.setObjectName("helpSection")
            layout.addWidget(section, 0, 0, 1, 2)
            for idx, (action, keys) in enumerate(actions, 1):
                left = QLabel(action)
                left.setObjectName("helpAction")
                right = QLabel(keys)
                right.setObjectName("helpGesture")
                right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                layout.addWidget(left, idx, 0)
                layout.addWidget(right, idx, 1)
            layout.setColumnStretch(0, 1)
            stack.addWidget(card)
        stack.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        bottom = QHBoxLayout()
        note = QLabel("Esc closes this window")
        note.setObjectName("helpLead")
        bottom.addWidget(note)
        bottom.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.hide)
        bottom.addWidget(close)
        outer.addLayout(bottom)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_F1, Qt.Key.Key_Escape) or (
            event.key() == Qt.Key.Key_H
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)
