"""
Unit tests for photo_archive CLI.
"""

import json
import tempfile
import unittest
from pathlib import Path
from src.photo_archive import (
    calculate_sha256,
    find_sidecars,
    scan_sources,
    SOURCE_CLASS_CATEGORY_MAP,
)


class TestPhotoArchive(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculate_sha256(self):
        test_file = self.root_path / "test.txt"
        test_file.write_bytes(b"hello photo archive")
        h = calculate_sha256(test_file)
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_find_sidecars(self):
        img = self.root_path / "photo1.jpg"
        img.write_bytes(b"image data")

        xmp = self.root_path / "photo1.xmp"
        xmp.write_bytes(b"xmp metadata")

        sidecars = find_sidecars(img)
        self.assertTrue(any("photo1.xmp" in s for s in sidecars))

    def test_scan_sources(self):
        src_folder = self.root_path / "photos"
        src_folder.mkdir()

        img1 = src_folder / "img1.jpg"
        img1.write_bytes(b"photo content 1")

        img2 = src_folder / "img2.mov"
        img2.write_bytes(b"video content 2")

        configs = [(src_folder, "icloud-export", "batch-01")]
        records = scan_sources(configs)

        self.assertEqual(len(records), 2)
        categories = [r["category"] for r in records]
        self.assertTrue(all(c == "01-icloud-photos" for c in categories))


if __name__ == "__main__":
    unittest.main()
