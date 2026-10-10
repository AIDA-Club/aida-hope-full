"""Task 5 polish: closing panel, About page, footer and Arabic review flag."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import booth

ROOT = Path(__file__).resolve().parents[1]


class PolishTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(booth, "RESULTS_PATH", Path(temp.name) / "results.csv")
        patcher.start()
        self.addCleanup(patcher.stop)

    def app(self, lang="en", page=None):
        app = AppTest.from_file(str(ROOT / "Home.py"), default_timeout=15).run()
        app.radio(key="language_choice").set_value(lang).run()
        if page:
            app.switch_page(f"pages/{page}").run()
        self.assertFalse(app.exception)
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertFalse(app.exception)

    def markdown_text(self, app):
        return " ".join(entry.value for entry in app.markdown)

    def test_arabic_ui_uses_plural_address(self):
        """Arabic UI text addresses visitors in the plural (اختاروا، إجابتكم), never the singular."""
        # Only forms that cannot be read another way. Words like اكتشف، تعلّم، شاهد، غيّر are left
        # out on purpose: they are also past tense ("the model detected / learned").
        singular = {"اختر", "اكتب", "اكشف", "اطلب", "اضغط", "استكشف", "انظر", "اطرح", "أعد", "اسأل",
                    "جرّب", "إجابتك", "سؤالك", "حالتك", "لصحتك", "إليك", "وصلت", "أنت", "تريد",
                    "أحتفظ", "أغيّر", "أحصل", "فاتك", "تفوقت", "بمساعدتك"}
        for key, value in booth.translations("ar").items():
            found = singular & set(re.findall(r"[؀-ۿ]+", value))
            self.assertFalse(found, f"{key}: singular form {sorted(found)} in {value!r}")

    def test_closing_panel_only_after_truth(self):
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            app = self.app(lang, "1_Challenge_Reveal.py")
            app.text_input(key="case_number").input("17")
            next(b for b in app.button if b.label == text["show_image"]).click().run()
            self.click(app, text["benign"])
            self.click(app, text["reveal_ai"])
            self.click(app, text["keep_answer"])
            self.assertNotIn(text["learn_line"], self.markdown_text(app))
            self.click(app, text["reveal_truth"])
            self.assertIn(text["learn_heading"], [s.value for s in app.subheader])
            self.assertIn(text["learn_line"], self.markdown_text(app))

    def test_about_page_uses_metrics_json(self):
        metrics = json.loads((ROOT / "data" / "reports" / "metrics.json").read_text(encoding="utf-8"))
        for lang in ("en", "ar"):
            app = self.app(lang, "4_About.py")
            self.assertEqual(app.title[0].value, booth.translations(lang)["about_title"])
            values = [metric.value for metric in app.metric]
            self.assertIn(str(metrics["n_test"]), values)
            self.assertIn(f"{metrics['accuracy'] * 100:.0f}%", values)
            self.assertIn(str(metrics["false_alarms"]), values)
            self.assertTrue(app.warning)  # the small-test-set note
            self.assertIn("doi:10.1016/j.dib.2019.104863", self.markdown_text(app))

    def test_footer_on_every_page(self):
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            for page in (None, "1_Challenge_Reveal.py", "2_Tweak_the_Tumor.py", "3_Ask_AIDA.py", "4_About.py"):
                app = self.app(lang, page)
                footer = next(m.value for m in app.markdown if 'class="booth-footer"' in m.value)
                self.assertIn(text["disclaimer"], footer)
                self.assertIn("BUSI", footer)
                self.assertIn("direction:rtl" if lang == "ar" else "direction:ltr", self.markdown_text(app))


if __name__ == "__main__":
    unittest.main()
