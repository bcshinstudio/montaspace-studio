"""Qt-free extension/UX contract tests for proposed media expansion."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def assignments():
    tree = ast.parse((ROOT / "app/config.py").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "IMAGE_FILTER", "SUPPORTED_EXTENSIONS", "VIDEO_FILTER", "VIDEO_EXTENSIONS"
                ):
                    values[target.id] = ast.literal_eval(node.value)
    return values


class MediaFormatContract(unittest.TestCase):
    def test_images_and_dialog_are_consistent(self):
        config = assignments()
        expected = {".png", ".jpg", ".jpeg", ".bmp", ".webp",
                    ".gif", ".tif", ".tiff", ".heic", ".heif", ".avif"}
        self.assertEqual(config["SUPPORTED_EXTENSIONS"], expected)
        for suffix in expected:
            self.assertIn("*" + suffix, config["IMAGE_FILTER"])

    def test_video_dialog_and_extensions(self):
        config = assignments()
        if "VIDEO_EXTENSIONS" not in config:
            self.assertNotIn("VIDEO_FILTER", config)
            return
        expected = {".mp4", ".mov", ".mkv", ".avi", ".webm",
                    ".wmv", ".m4v", ".mpg", ".mpeg"}
        self.assertEqual(config["VIDEO_EXTENSIONS"], expected)
        for suffix in expected:
            self.assertIn("*" + suffix, config["VIDEO_FILTER"])

    def test_import_failure_has_feedback(self):
        source = (ROOT / "app/canvas.py").read_text(encoding="utf-8")
        self.assertIn('"Cannot open image"', source)
        self.assertIn("QMessageBox.warning", source)

    def test_documentation_discloses_codec_limitations(self):
        doc = (ROOT / "docs/MEDIA_FORMAT_SUPPORT.md").read_text(encoding="utf-8")
        self.assertIn("actual", doc)
        self.assertIn("HEIC", doc)
        self.assertIn("verified release", doc)


if __name__ == "__main__":
    unittest.main()
