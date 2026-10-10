"""public_app.py: the public website (Challenge, Tweak the Tumor, Ask AIDA, About) in public mode."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import booth

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_public  # noqa: E402

PAGES = ("pages/1_Challenge_Reveal.py", "pages/2_Tweak_the_Tumor.py", "pages/3_Ask_AIDA.py", "pages/4_About.py")
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


class WriteRecorder:
    """Records every file write attempted while active (audit hooks cannot be removed, so gate them)."""

    active = False
    writes: list = []

    @classmethod
    def hook(cls, event, args):
        if not cls.active:
            return
        if event == "open":
            path, mode, flags = args
            if isinstance(path, int):
                return
            if (mode and any(c in str(mode) for c in "wax+")) or (mode is None and flags & WRITE_FLAGS):
                cls.writes.append((event, str(path)))
        elif event in ("os.rename", "os.replace", "os.remove", "os.mkdir", "os.truncate", "shutil.copyfile",
                       "shutil.rmtree", "os.unlink"):
            cls.writes.append((event, str(args[0])))


sys.addaudithook(WriteRecorder.hook)


def public_app(lang="en", page=None):
    app = AppTest.from_file(str(ROOT / "public_app.py"), default_timeout=30).run()
    if lang != "en":
        app.radio(key="language_choice").set_value(lang).run()
    if page:
        app.switch_page(page).run()
    return app


def click(app, key=None, label=None):
    button = app.button(key=key) if key else next(b for b in app.button if b.label == label)
    button.click().run()
    assert not app.exception, app.exception
    return app


def texts(app):
    return " ".join([m.value for m in app.markdown] + [c.value for c in app.caption] + [e.value for e in app.error]
                    + [i.value for i in app.info] + [s.value for s in app.subheader] + [w.value for w in app.title])


def play_case(app, answer="normal"):
    click(app, key=f"pick_{answer}")
    click(app, key="public_reveal_ai")
    click(app, key="public_reveal_truth")
    click(app, key="public_next")


class PublicAppTests(unittest.TestCase):
    def test_pages_render_in_both_languages(self):
        for lang in ("en", "ar"):
            app = public_app(lang)
            self.assertFalse(app.exception, lang)
            self.assertIn(booth.translations(lang)["public_home_intro"], texts(app))
            for page in PAGES:
                app.switch_page(page).run()
                self.assertFalse(app.exception, (lang, page))
                footer = next(m.value for m in app.markdown if 'class="booth-footer"' in m.value)
                self.assertIn(booth.translations(lang)["disclaimer"], footer)

    def test_navigation_titles(self):
        source = (ROOT / "public_app.py").read_text(encoding="utf-8")
        for key in ("home_title", "public_challenge_title", "tweak_title", "ask_title", "about_title"):
            self.assertIn(f't("{key}")', source)
        for private in ("results.csv", "booth_key", "booth_keyboard", "answer_key"):
            self.assertNotIn(private, source)

    def test_card_number_lookup(self):
        for number in range(1, 31):
            for text in (str(number), f"{number:02d}", f"#{number}", f" {number} "):
                self.assertEqual(booth.card_case_id(text), f"{number:02d}", text)
        self.assertEqual(booth.card_case_id("١٧"), "17")  # Arabic-Indic digits from a phone keyboard
        for text in ("0", "00", "31", "100", "-1", "7.0", "abc", "", " ", "²", "1 2", None, 7):
            self.assertIsNone(booth.card_case_id(text), text)

    def test_card_entry_plays_that_case_and_rejects_others_politely(self):
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            app = public_app(lang, PAGES[0])
            for bad in ("31", "0", "abc"):
                app.text_input(key="card_number").input(bad)
                click(app, label=text["play_card"])
                self.assertEqual([e.value for e in app.error], [text["card_invalid"]], bad)
            app.text_input(key="card_number").input("7")
            click(app, label=text["play_card"])
            self.assertIn(text["round_progress"].format(current=1, total=1, card=7), texts(app))
            self.assertTrue(app.button(key="public_reveal_ai").disabled)  # locked until they choose
            click(app, key="pick_benign")
            self.assertFalse(app.button(key="public_reveal_ai").disabled)
            click(app, key="public_reveal_ai")
            self.assertIn(text["ai_prediction"].format(prediction=text["malignant"]), texts(app))
            click(app, key="public_reveal_truth")
            # Card 07: benign, AI said malignant: a false alarm, and the visitor beat the AI.
            self.assertIn(text["truth_heading"].format(truth=text["benign"]), texts(app))
            self.assertIn(text["score_line"].format(you=1, ai=0, total=1), texts(app))
            self.assertIn(text["explain_false_alarm"].split("{")[0], texts(app))
            click(app, key="public_next")
            self.assertIn(text["station_message"], texts(app))
            click(app, key="play_again")
            self.assertIsNotNone(app.button(key="play_round"))

    def test_round_of_five_scores_and_ends(self):
        text = booth.translations("en")
        app = public_app("en", PAGES[0])
        click(app, key="play_round")
        state = app.session_state["public_round"]
        cases = state["cases"]
        self.assertEqual(len(cases), 5)
        self.assertEqual(len({case["case_id"] for case in cases}), 5)
        for _ in range(5):
            play_case(app, "normal")
        you = sum(case["truth"] == "normal" for case in cases)
        ai = sum(case["correct"] for case in cases)
        self.assertIn(text["score_line"].format(you=you, ai=ai, total=5), texts(app))
        self.assertIn(text["station_message"], texts(app))
        self.assertIn(text["learn_line"], texts(app))

    def test_public_challenge_has_no_staff_controls(self):
        app = public_app("en", PAGES[0])
        keys = {button.key for button in app.button}
        self.assertNotIn("next_visitor", keys)
        self.assertNotIn("case_number", {box.key for box in app.text_input} - {"card_number"})
        source = " ".join(m.value for m in app.markdown)
        self.assertNotIn("__aidaBoothKeyHandler", source)
        self.assertIn(booth.translations("en")["case_credits"],
                      next(m.value for m in app.markdown if 'class="booth-footer"' in m.value))

    def test_all_six_patient_folders(self):
        folders = [line for line in (ROOT / "print_content.yaml").read_text(encoding="utf-8").splitlines()
                   if line.startswith("  - number:")]
        self.assertEqual(len(folders), 6)
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            app = public_app(lang, PAGES[0])
            app.toggle(key="show_wrong").set_value(True).run()
            self.assertFalse(app.exception)
            for number, cid in enumerate(("17", "25", "26", "28", "04", "folder6"), start=1):
                self.assertIn(text[f"wrong_{cid}_text"], texts(app))
                self.assertIn(text["folder_label"].format(n=number), texts(app))

    def test_folder6_matches_the_model_predictions(self):
        import csv
        import json
        folder = json.loads((ROOT / "data" / "folders" / "folder6.json").read_text(encoding="utf-8"))
        with (ROOT / "data" / "reports" / "predictions.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["file_name"] == folder["source_file"])
        self.assertEqual(folder["source_file"], "malignant_id_153.png")  # print_content.yaml folder 6
        self.assertEqual((folder["truth"], folder["ai_pred"]), (row["truth"], row["pred"]))
        for label in booth.CLASSES:
            self.assertAlmostEqual(folder["ai_probs"][label], float(row[f"prob_{label}"]))
        self.assertAlmostEqual(folder["cam_mask_overlap"], float(row["cam_mask_overlap"]))

    def test_explanations_follow_the_data(self):
        """Every case gets one line; "wrong reason" only from a measured overlap under 0.1, never normal."""
        import json
        # The page's helpers without its last line (which would draw the page).
        source = (ROOT / PAGES[0]).read_text(encoding="utf-8").replace("\nchallenge()\n", "\n")
        namespace = {}
        exec(compile(source, PAGES[0], "exec"), namespace)
        cases = json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            with patch.object(booth.st, "session_state", {"lang": lang}):
                lines = {case["case_id"]: namespace["explanation"](case) for case in cases}
            self.assertEqual(len(lines), 30)
            for case in cases:
                wrong_reason = lines[case["case_id"]] == text["explain_right_wrong_place"]
                expected = (case["correct"] and case["truth"] != "normal"
                            and case["cam_mask_overlap"] is not None and case["cam_mask_overlap"] < 0.1)
                self.assertEqual(wrong_reason, expected, case["case_id"])
                if case["truth"] == "normal":
                    self.assertNotIn(lines[case["case_id"]], (text["explain_right_on_target"],
                                     text["explain_right_partly"], text["explain_right_wrong_place"]))
            unmeasured = dict(cases[0], cam_mask_overlap=None)  # a lesion with no overlap value
            with patch.object(booth.st, "session_state", {"lang": lang}):
                self.assertEqual(namespace["explanation"](unmeasured), text["explain_right"])

    def test_public_mode_never_writes_files(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(booth, "RESULTS_PATH", Path(temporary) / "results.csv"):
            WriteRecorder.writes = []
            WriteRecorder.active = True
            try:
                (Path(temporary) / "probe.txt").write_text("x", encoding="utf-8")
                self.assertEqual(len(WriteRecorder.writes), 1)  # the recorder does see writes
                WriteRecorder.writes = []
                app = public_app("en", PAGES[0])
                click(app, key="play_round")
                for _ in range(5):
                    play_case(app, "malignant")
                click(app, key="play_again")
                app.text_input(key="card_number").input("17")
                click(app, label=booth.translations("en")["play_card"])
                play_case(app, "benign")
                app.switch_page(PAGES[1]).run()
                app.slider(key="feature_mean radius").set_value(20.0).run()
                click(app, key="reset_malignant")
                app.switch_page(PAGES[2]).run()
                app.switch_page(PAGES[3]).run()
            finally:
                WriteRecorder.active = False
            self.assertFalse(app.exception)
            self.assertFalse((Path(temporary) / "results.csv").exists())
        self.assertEqual(WriteRecorder.writes, [])

    def test_save_round_refuses_in_public_mode(self):
        app = public_app("en", PAGES[0])
        self.assertTrue(app.session_state["public_mode"])
        with patch.object(booth.st, "session_state", {"public_mode": True}):
            with self.assertRaises(booth.BoothError):
                booth.save_round({"logged": False, "case": {}})


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.dest = Path(cls.temp.name)
        (cls.dest / ".devcontainer").mkdir()
        (cls.dest / ".devcontainer" / "devcontainer.json").write_text("{}", encoding="utf-8")
        cls.files = export_public.export(cls.dest)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_contains_the_public_games(self):
        expected = {"public_app.py", "booth.py", "slide_image.py", "aida_chat.py", "requirements.txt",
                    "data/booth_set.json", "models/wdbc_model.pkl", "models/wdbc_features.json",
                    "data/slide/base.jpg", "data/slide/background.jpg", "data/slide/nuclei.json",
                    "data/slide/reference_malignant.jpg", "data/folders/folder6.json",
                    "data/folders/folder6_overlay.png", *PAGES}
        for number in range(1, 31):
            for folder in ("images", "heatmaps", "overlays"):
                expected.add(f"data/{folder}/case{number:02d}.png")
        self.assertLessEqual(expected, set(self.files))

    def test_excludes_private_files(self):
        for name in self.files:
            lowered = name.lower()
            for word in ("results", "answer", "booth_key", "predictions", "gradcam", "print", "docs/",
                         "secrets.toml", "_old", "booth_set_demo", "booth_keyboard", "split.csv"):
                self.assertNotIn(word, lowered, name)
            self.assertFalse(lowered.endswith((".pdf", ".pt", ".csv", ".zip", ".log")), name)
            if name.startswith("models/"):
                self.assertIn(name, ("models/wdbc_model.pkl", "models/wdbc_features.json"))

    def test_keeps_the_public_repos_own_folders(self):
        self.assertTrue((self.dest / ".devcontainer" / "devcontainer.json").is_file())

    def test_requirements_pin_the_model_stack(self):
        lines = (self.dest / "requirements.txt").read_text(encoding="utf-8").splitlines()
        pins = dict(line.split("==") for line in lines if "==" in line)
        for package in ("streamlit", "scikit-learn", "numpy", "scipy", "pandas", "openai"):
            self.assertIn(package, pins)
        self.assertEqual(pins["scikit-learn"], "1.6.1")


if __name__ == "__main__":
    unittest.main()
