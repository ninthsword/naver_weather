"""Regression checks for third-party dependency compatibility."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY / "custom_components" / "naver_weather_custom" / "manifest.json"


class DependencyCompatibilityTest(unittest.TestCase):
    """Keep the pinned parser compatible with the Home Assistant runtime."""

    def test_manifest_pins_python_3_beautifulsoup_release(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertIn("beautifulsoup4==4.13.3", manifest["requirements"])

    def test_real_package_exposes_tag_for_css_selection(self):
        script = (
            "from importlib.metadata import version; "
            "assert version('beautifulsoup4') == '4.13.3'; "
            "import bs4; "
            "from bs4 import BeautifulSoup; "
            "assert hasattr(bs4, 'Tag'); "
            "soup = BeautifulSoup('<div><span>ok</span></div>', 'html.parser'); "
            "assert soup.select_one('div > span').text == 'ok'"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
