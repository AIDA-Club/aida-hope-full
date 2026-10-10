import ast
import csv
import json
import pickle
import string
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image  # Installed by Streamlit; used only to verify PNG assets.
from streamlit.testing.v1 import AppTest

import aida_chat
import booth

ROOT = booth.ROOT


class FixtureModel:
    classes_ = ["benign", "malignant"]  # Deliberately reversed WDBC order.
    n_features_in_ = 6

    def predict_proba(self, rows):
        probability = rows[0][0] / 10
        return [[1 - probability, probability]]


FEATURES = [{"name": f"feature_{i}", "min": 0.0, "max": 10.0, "median": 5.0,
             "labels": {"en": f"Measurement {i}", "ar": f"القياس {i}"}} for i in range(6)]


class BoothTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.results = Path(self.temp.name) / "results.csv"
        self.patcher = patch.object(booth, "RESULTS_PATH", self.results)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def app(self, page=None):
        app = AppTest.from_file(str(ROOT / "Home.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        if page:
            app.switch_page(f"pages/{page}").run()
            self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        matches = [button for button in app.button if button.label == label]
        self.assertEqual(len(matches), 1, (label, [button.label for button in app.button]))
        matches[0].click().run()
        self.assertFalse(app.exception)

    def begin(self, app, cid="01"):
        app.text_input(key="case_number").input(cid)
        self.button(app, "Show image")

    def rows(self):
        if not self.results.exists():
            return []
        with self.results.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def banner(self, app):
        return next(entry.value for entry in app.markdown if 'class="booth-result"' in entry.value)

    def test_translations_and_python_311_syntax(self):
        en, ar = booth.translations("en"), booth.translations("ar")
        # Keys starting with "_" are file metadata (e.g. the Arabic review status), not UI text.
        self.assertEqual({k for k in en if not k.startswith("_")}, {k for k in ar if not k.startswith("_")})
        self.assertEqual(ar["_review_status"], "DRAFT - needs native Arabic review")
        for key in (k for k in en if not k.startswith("_")):
            placeholders = lambda text: {name for _, name, _, _ in string.Formatter().parse(text) if name}
            self.assertEqual(placeholders(en[key]), placeholders(ar[key]), key)
        for file in [ROOT / "Home.py", ROOT / "booth.py", ROOT / "booth_keyboard.py",
                     *ROOT.glob("pages/*.py"), *ROOT.glob("scripts/*.py")]:
            tree = ast.parse(file.read_text(encoding="utf-8"), feature_version=(3, 11))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, en)

    def test_dataset_and_all_pngs(self):
        cases = booth.load_cases()
        self.assertEqual(set(cases), {f"{i:02d}" for i in range(1, 31)})
        self.assertEqual({case["error_type"] for case in cases.values()},
                         {None, "false_negative", "false_positive", "other_confusion"})
        for case in cases.values():
            for field in ("image", "heatmap", "mask_overlay", "print_image"):
                with Image.open(booth.asset_path(case[field])) as image:
                    image.verify()

    def test_home_language_and_navigation(self):
        app = self.app()
        self.assertEqual(len(app.button), 3)
        app.radio(key="language_choice").set_value("ar").run()
        self.assertFalse(app.exception)
        self.assertIn("direction:rtl", " ".join(m.value for m in app.markdown))
        self.button(app, booth.translations("ar")["ask_title"])
        self.assertEqual(app.title[0].value, booth.translations("ar")["ask_title"])

    def test_keep_flow_reveal_order_csv_and_reset(self):
        app = self.app("1_Challenge_Reveal.py")
        self.begin(app)
        self.assertEqual(len(app.get("image")), 1)
        self.assertFalse(self.results.exists())
        self.button(app, "Malignant")
        self.assertNotIn("Reveal truth", [button.label for button in app.button])
        heatmap_line = booth.translations("en")["heatmap_disclaimer"]
        self.assertNotIn(heatmap_line, [caption.value for caption in app.caption])
        self.button(app, "Reveal AI")
        self.assertEqual(len(app.get("progress")), 3)
        self.assertEqual([caption.value for caption in app.caption].count(heatmap_line), 1)
        self.button(app, "Keep my answer")
        self.assertFalse(self.results.exists())
        self.button(app, "Reveal truth")
        self.assertEqual(self.rows()[0]["final_answer"], "malignant")
        self.assertIn(booth.translations("en")["both_right"], self.banner(app))
        app.run()
        self.assertEqual(len(self.rows()), 1)
        self.button(app, "Next visitor")
        self.assertNotIn("round", app.session_state)
        self.assertEqual(app.text_input(key="case_number").value, "")
        self.begin(app)
        for label in ("Benign", "Reveal AI", "Keep my answer", "Reveal truth"):
            self.button(app, label)
        self.assertEqual(len(self.rows()), 2)

    def test_change_flow_and_arabic_midround(self):
        app = self.app("1_Challenge_Reveal.py")
        self.begin(app, "17")  # Truth malignant, AI benign.
        self.button(app, "Benign")
        self.button(app, "Reveal AI")
        self.button(app, "Change my answer")
        app.radio(key="language_choice").set_value("ar").run()
        self.button(app, "خبيث")
        self.button(app, booth.translations("ar")["reveal_truth"])
        row = self.rows()[0]
        self.assertEqual((row["case_id"], row["first_answer"], row["ai_pred"], row["final_answer"], row["truth"]),
                         ("17", "benign", "benign", "malignant", "malignant"))
        self.assertIn(booth.translations("ar")["visitor_right"], self.banner(app))
        app.switch_page("pages/3_Ask_AIDA.py").run()
        app.switch_page("pages/1_Challenge_Reveal.py").run()
        self.assertEqual(len(self.rows()), 1)
        self.button(app, "الزائر التالي")
        self.assertEqual(app.session_state["lang"], "ar")

    def test_both_wrong_learning_message(self):
        app = self.app("1_Challenge_Reveal.py")
        self.begin(app, "17")
        for label in ("Normal", "Reveal AI", "Keep my answer", "Reveal truth"):
            self.button(app, label)
        self.assertIn(booth.translations("en")["both_wrong"], self.banner(app))

    def test_invalid_case_and_save_retry(self):
        app = self.app("1_Challenge_Reveal.py")
        self.begin(app, "99")
        self.assertEqual(app.error[0].value, booth.translations("en")["case_invalid"])
        self.begin(app, "01")
        for label in ("Normal", "Reveal AI", "Keep my answer"):
            self.button(app, label)
        with patch.object(booth, "save_round", side_effect=PermissionError):
            self.button(app, "Reveal truth")
        self.assertTrue(app.error)
        self.assertTrue(next(b for b in app.button if b.label == "Next visitor").disabled)
        self.button(app, "Retry saving")
        self.assertEqual(len(self.rows()), 1)
        self.assertIn(booth.translations("en")["ai_right"], self.banner(app))

    def test_offline_topics_both_languages(self):
        app = self.app("3_Ask_AIDA.py")
        for lang in ("en", "ar"):
            app.radio(key="language_choice").set_value(lang).run()
            for topic in ("know_signs", "myth_fact", "explain_term", "get_help"):
                self.button(app, booth.translations(lang)[topic])
                expected = aida_chat.fallback_sections(lang)[topic]
                self.assertIn(expected, [entry.value for entry in app.markdown])

    def test_coming_soon_and_live_model(self):
        is_file = Path.is_file
        with patch.object(Path, "is_file", lambda p: False if p.name == "wdbc_model.pkl" else is_file(p)):
            app = self.app("2_Tweak_the_Tumor.py")
        self.assertEqual(app.info[0].value, "Coming soon")
        fixture_medians = {label: {f["name"]: value for f in FEATURES}
                           for label, value in (("benign", 2.5), ("malignant", 7.5))}
        with patch.object(booth, "load_model_bundle", return_value=(FixtureModel(), FEATURES, ["benign", "malignant"])), patch.object(
                booth, "load_class_medians", return_value=fixture_medians):
            app = self.app("2_Tweak_the_Tumor.py")
            self.assertEqual(len(app.slider), 6)
            app.slider(key="feature_feature_0").set_value(8.0).run()
            self.assertTrue(any('class="booth-gauge-number">80%' in entry.value for entry in app.markdown))
            self.assertIn("Malignant", app.subheader[-1].value)
            app.slider(key="decision_threshold").set_value(0.9).run()
            self.assertIn("Benign", app.subheader[-1].value)
            self.assertEqual(app.get("progress")[0].proto.value, 80)

    def test_real_model_presets_and_friendly_labels(self):
        app = self.app("2_Tweak_the_Tumor.py")
        self.assertFalse(app.error)
        self.assertEqual([slider.label for slider in app.slider[:5]],
                         ["Nucleus size", "Texture", "Smoothness", "Concavity", "Concave points"])
        model, features, labels = booth.load_model_bundle()
        medians = booth.load_class_medians(features)
        for label in ("benign", "malignant"):
            self.button(app, booth.translations("en")[f"reset_{label}"])
            values = [slider.value for slider in app.slider[:5]]
            self.assertEqual(values, [medians[label][f["name"]] for f in features])
            self.assertEqual(app.slider(key="decision_threshold").value, 0.5)
            probability = booth.malignant_probability(model, values, labels)
            self.assertLess(probability, 0.1) if label == "benign" else self.assertGreater(probability, 0.9)

    def test_normal_case_and_overlap_boundaries(self):
        app = self.app("1_Challenge_Reveal.py")
        self.begin(app, "02")
        for label in ("Normal", "Reveal AI", "Keep my answer", "Reveal truth"):
            self.button(app, label)
        self.assertEqual(len(app.get("image")), 3)
        self.assertFalse(any("Did the AI look" in entry.value for entry in app.markdown))
        for overlap, expected in ((0.099, "No, it focused elsewhere"), (0.1, "Partly"),
                                  (0.299, "Partly"), (0.3, "Yes, mostly"), (None, None)):
            case = dict(booth.load_cases()["01"], cam_mask_overlap=overlap)
            app.session_state["round"] = {"case": case, "phase": "done", "first_answer": "malignant",
                                           "final_answer": "malignant", "logged": False}
            app.run()
            self.assertFalse(app.exception)
            lines = [entry.value for entry in app.markdown if "Did the AI look" in entry.value]
            self.assertIn(expected, lines[0]) if expected else self.assertFalse(lines)

    def test_all_originals_and_contextual_validation(self):
        with (ROOT / "data/reports/predictions.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 68)
        for row in rows:
            with Image.open(ROOT / "data/reports/gradcam_all/originals" / row["file_name"]) as image:
                image.verify()
        cases = list(booth.load_cases().values())
        fixture_root = Path(self.temp.name)
        (fixture_root / "data").mkdir()
        for field, value, remove in (("heatmap", None, True), ("cam_mask_overlap", -1, False),
                                     ("ai_probs", {"normal": True, "benign": 0.0, "malignant": 0.0}, False)):
            changed = json.loads(json.dumps(cases))
            if remove:
                del changed[0][field]
            else:
                changed[0][field] = value
            (fixture_root / "data/booth_set.json").write_text(json.dumps(changed), encoding="utf-8")
            with patch.object(booth, "ROOT", fixture_root):
                with self.assertRaises(booth.BoothError) as error:
                    booth.load_cases()
            self.assertEqual(error.exception.case_id, "01")
            self.assertTrue(error.exception.field.startswith(field))

    def test_model_metadata_loader_and_bad_assets(self):
        fixture_root = Path(self.temp.name)
        models = fixture_root / "models"
        models.mkdir()
        (models / "wdbc_features.json").write_text(json.dumps({"features": FEATURES}), encoding="utf-8")
        (models / "wdbc_model.pkl").write_bytes(pickle.dumps(FixtureModel()))
        with patch.object(booth, "ROOT", fixture_root):
            model, features, labels = booth.load_model_bundle()
            self.assertEqual(labels, ["benign", "malignant"])
            self.assertEqual(booth.malignant_probability(model, [8.0] + [5.0] * 5, labels), 0.8)
            with self.assertRaises(booth.BoothError):
                booth.asset_path("../outside.png")
            with self.assertRaises(booth.BoothError):
                booth.load_cases()


if __name__ == "__main__":
    unittest.main()
