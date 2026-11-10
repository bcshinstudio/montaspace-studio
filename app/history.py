"""Memory-conscious Qt undo command."""
from PySide6.QtGui import QUndoCommand


class StateCommand(QUndoCommand):
    """Undo one edit by storing small metadata snapshots, not image bytes."""

    def __init__(self, canvas, before, after, name):
        super().__init__(name)
        self.canvas = canvas
        self.before = before
        self.after = after
        self.first_redo = True

    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return  # The user already performed the action.
        self.canvas.restore_state(self.after)

    def undo(self):
        self.canvas.restore_state(self.before)
