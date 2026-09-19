"""Unit tests for provider chain fallthrough and graceful degradation."""

import unittest
from images.pollinations import PollinationsProvider
from images.pillow_art import PillowArtProvider


class TestProviderChain(unittest.TestCase):
    def test_provider_chain_fallthrough(self):
        # Pollinations without API key is exhausted / unavailable
        pollinations = PollinationsProvider()
        pollinations.is_exhausted = True

        pillow = PillowArtProvider()

        chain = [pollinations, pillow]
        prompt = "Ancient Indian temple carvings in morning mist"
        seed = 42

        chosen_img = None
        used_provider = None

        for prov in chain:
            if prov.is_available():
                img = prov.generate(prompt, seed=seed)
                if img is not None:
                    chosen_img = img
                    used_provider = prov.name()
                    break

        self.assertIsNotNone(chosen_img)
        self.assertEqual(used_provider, "pillow")
        self.assertEqual(chosen_img.size, (1024, 1280))


if __name__ == "__main__":
    unittest.main()
