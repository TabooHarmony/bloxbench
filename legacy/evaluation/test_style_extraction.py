import unittest
from pathlib import Path

from style_extraction import extract_style_profile, style_profile_prompt


class StyleExtractionTests(unittest.TestCase):
    def test_extracts_concrete_tokens_from_reference_ui(self):
        source = Path("Reference/VB_UI_002_daily_reward_ref.lua")
        profile = extract_style_profile([source])

        self.assertEqual(profile["schema_version"], "1")
        self.assertEqual(len(profile["sources"]), 1)
        self.assertEqual(profile["sources"][0]["path"], str(source))
        self.assertIn("ScreenGui", profile["component_counts"])
        self.assertIn("UICorner", profile["component_counts"])
        self.assertIn("GothamBold", profile["font_usage"])
        self.assertIn("28", profile["text_sizes"])
        self.assertIn("30,30,40", profile["colors"])
        self.assertIn("12", profile["corner_radii_px"])

    def test_prompt_labels_extracted_values_as_local_observations(self):
        profile = extract_style_profile([
            Path("Reference/VB_UI_002_daily_reward_ref.lua"),
            Path("Reference/VB_UI_003_trade_window_ref.lua"),
        ])
        prompt = style_profile_prompt(profile)

        self.assertIn("reference-derived style signals", prompt)
        self.assertIn("local observations", prompt)
        self.assertIn("do not copy blindly", prompt)
        self.assertIn("GothamBold", prompt)
        self.assertIn("30,30,40", prompt)


if __name__ == "__main__":
    unittest.main()
