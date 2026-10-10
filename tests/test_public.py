"""public_app.py serves only Ask AIDA and About, in both languages."""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class PublicAppTests(unittest.TestCase):
    def test_pages_render_in_both_languages(self):
        app = AppTest.from_file(str(ROOT / "public_app.py"), default_timeout=20).run()
        for lang in ("en", "ar"):
            app.radio(key="language_choice").set_value(lang).run()
            for page in ("pages/3_Ask_AIDA.py", "pages/4_About.py"):
                app.switch_page(page).run()
                self.assertFalse(app.exception, (lang, page))

    def test_entry_only_references_public_pages(self):
        source = (ROOT / "public_app.py").read_text(encoding="utf-8").split('"""')[2]  # code, not docstring
        for private in ("1_Challenge", "2_Tweak", "booth_set", "results.csv"):
            self.assertNotIn(private, source)


if __name__ == "__main__":
    unittest.main()
