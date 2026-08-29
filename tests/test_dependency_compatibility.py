"""Regression checks for third-party dependency compatibility."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY / "custom_components" / "naver_weather_custom" / "manifest.json"
COMPATIBILITY = (
    REPOSITORY / "custom_components" / "naver_weather_custom" / "bs4_compat.py"
)


class DependencyCompatibilityTest(unittest.TestCase):
    """Keep the pinned parser compatible with the Home Assistant runtime."""

    def test_manifest_pins_python_3_beautifulsoup_release(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertIn("beautifulsoup4==4.13.3", manifest["requirements"])

    def _run_real_package(self, script):
        result = subprocess.run(
            [sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_package_normal_path_exposes_tag_for_css_selection(self):
        script = f"""
            from importlib.metadata import version
            import importlib.util
            assert version("beautifulsoup4") == "4.13.3"
            import bs4
            from bs4 import BeautifulSoup
            from bs4.element import Tag
            spec = importlib.util.spec_from_file_location("compat", {str(COMPATIBILITY)!r})
            compat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(compat)
            assert bs4.Tag is Tag
            soup = BeautifulSoup("<div><span>ok</span></div>", "html.parser")
            assert soup.select_one("div > span").text == "ok"
        """
        self._run_real_package(script)

    def test_real_package_missing_tag_is_repaired_for_css_selection(self):
        script = f"""
            from importlib.metadata import version
            import importlib.util
            assert version("beautifulsoup4") == "4.13.3"
            import bs4
            from bs4 import BeautifulSoup
            from bs4.element import Tag
            del bs4.Tag
            assert not hasattr(bs4, "Tag")
            spec = importlib.util.spec_from_file_location("compat", {str(COMPATIBILITY)!r})
            compat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(compat)
            assert bs4.Tag is Tag
            soup = BeautifulSoup("<div><span>ok</span></div>", "html.parser")
            assert soup.select_one("div > span").text == "ok"
        """
        self._run_real_package(script)


if __name__ == "__main__":
    unittest.main()
