"""Static regressions for the single hover/drag resolver (no Qt needed)."""
import ast
import unittest
from pathlib import Path

CANVAS = Path(__file__).resolve().parents[1] / "app" / "canvas.py"


class CursorDragIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CANVAS.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.canvas = next(node for node in cls.tree.body if isinstance(node, ast.ClassDef) and node.name == "Canvas")

    def method(self, name):
        return next(node for node in self.canvas.body if isinstance(node, ast.FunctionDef) and node.name == name)

    def called_methods(self, name):
        return {node.func.attr for node in ast.walk(self.method(name))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}

    def test_cursor_and_mouse_press_share_resolver(self):
        self.assertIn("_selected_grip_at", self.called_methods("mouseMoveEvent"))
        self.assertIn("_selected_grip_at", self.called_methods("mousePressEvent"))

    def test_view_captures_entire_drag(self):
        self.assertIn("_begin_grip_drag", self.called_methods("mousePressEvent"))
        self.assertIn("_move_grip_drag", self.called_methods("mouseMoveEvent"))
        self.assertIn("_end_grip_drag", self.called_methods("mouseReleaseEvent"))

    def test_photo_undo_and_video_title_update_remain(self):
        self.assertIn("record_edit", self.called_methods("_end_grip_drag"))
        self.assertIn("update_modified_title", self.called_methods("_end_grip_drag"))

    def test_existing_geometry_modules_not_modified(self):
        # Geometry math remains delegated to the media item and existing hit function.
        self.assertIn("handle_at", self.called_methods("_selected_grip_at"))
        self.assertIn("_refresh_selection_geometry", self.called_methods("_move_grip_drag"))
        self.assertIn("_refresh_handles", self.called_methods("_move_grip_drag"))


if __name__ == "__main__":
    unittest.main()
