"""Unit tests for ImageNormalizer aspect ratio and dimension enforcement."""

import unittest
from PIL import Image
from images.normalize import ImageNormalizer


class TestImageNormalizer(unittest.TestCase):
    def test_normalizer_outputs_1080x1350(self):
        test_cases = [
            ("native_4_5", (1024, 1280)),
            ("square_1_1", (1024, 1024)),
            ("landscape_16_9", (1920, 1080)),
            ("ultra_portrait", (600, 1200)),
            ("exact_target", (1080, 1350))
        ]

        for name, size in test_cases:
            with self.subTest(name=name, size=size):
                test_img = Image.new("RGB", size, color=(100, 150, 200))
                norm = ImageNormalizer.normalize(test_img)

                # Assert exact dimensions
                self.assertEqual(norm.size, (1080, 1350))
                self.assertEqual(norm.mode, "RGB")

                # Assert ratio is 0.8
                ratio = norm.size[0] / norm.size[1]
                self.assertAlmostEqual(ratio, 0.8, places=4)
                self.assertTrue(0.8 <= ratio <= 1.91)


if __name__ == "__main__":
    unittest.main()
