"""The web API (api/main.py) against the original Python functions it wraps.

Parity: every prediction, probability, explanation and chat answer must be exactly what the
Streamlit app's own functions produce for the same input. No network calls are made: the live
chat path is exercised with a stand-in for aida_chat.call_llm.
"""
import json
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import aida_chat as chat  # noqa: E402
import booth  # noqa: E402
import challenge_logic as rules  # noqa: E402
import slide_image  # noqa: E402
from api import main as api  # noqa: E402

CASES = {case["case_id"]: case for case in json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))}


def client() -> TestClient:
    return TestClient(api.app)


class TweakParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.features, cls.labels = booth.load_model_bundle()
        cls.medians = booth.load_class_medians(cls.features)
        rng = random.Random(20261011)
        five = cls.features[:5]
        cls.fixtures = [
            [f["median"] for f in five],
            [cls.medians["benign"][f["name"]] for f in five],
            [cls.medians["malignant"][f["name"]] for f in five],
            [f["min"] for f in five],
            [f["max"] for f in five],
        ] + [[round(rng.uniform(f["min"], f["max"]), 4) for f in five] for _ in range(40)]

    def test_probabilities_match_the_original_model_call(self):
        web = client()
        for values in self.fixtures:
            expected = booth.malignant_probability(self.model, values, self.labels)
            reply = web.post("/api/tweak/predict", json={"values": values, "threshold": 0.5}).json()
            self.assertEqual(reply["malignant"], expected, values)  # exact, not approximate
            self.assertEqual(reply["benign"], 1 - expected)

    def test_threshold_changes_the_decision_not_the_probability(self):
        web = client()
        values = self.fixtures[0]
        probability = booth.malignant_probability(self.model, values, self.labels)
        for threshold in (0.0, 0.01, 0.25, 0.5, 0.75, 0.99, 1.0, probability):
            reply = web.post("/api/tweak/predict", json={"values": values, "threshold": threshold}).json()
            self.assertEqual(reply["malignant"], probability)
            expected = "malignant" if probability >= threshold else "benign"  # at the threshold: malignant
            self.assertEqual(reply["prediction"], expected, threshold)
            self.assertEqual(reply["confidence"], probability if expected == "malignant" else 1 - probability)

    def test_presets_and_feature_order_come_from_the_metadata(self):
        model = client().get("/api/tweak/model").json()
        self.assertTrue(model["available"])
        self.assertEqual([f["name"] for f in model["features"]], [f["name"] for f in self.features[:5]])
        self.assertEqual([f["key"] for f in model["features"]],
                         ["nucleus_size", "texture", "smoothness", "concavity", "concave_points"])
        for label in ("benign", "malignant"):
            self.assertEqual(model["presets"][label], [self.medians[label][f["name"]] for f in self.features[:5]])
        self.assertEqual(model["default_threshold"], 0.5)

    def test_out_of_range_and_wrong_length_inputs_are_refused(self):
        web = client()
        too_big = [f["max"] + 1 for f in self.features[:5]]
        self.assertEqual(web.post("/api/tweak/predict", json={"values": too_big}).status_code, 422)
        self.assertEqual(web.post("/api/tweak/predict", json={"values": [1, 2]}).status_code, 422)
        self.assertEqual(web.post("/api/tweak/predict", json={"values": self.fixtures[0], "threshold": 2}).status_code, 422)

    def test_microscope_image_is_the_original_renderer(self):
        values = self.fixtures[2]
        names = [f["name"] for f in self.features]
        look = slide_image.look_for(dict(zip(names, values)), {f["name"]: f for f in self.features}, self.medians["benign"])
        reply = client().get("/api/tweak/slide", params={"values": ",".join(map(str, values))})
        self.assertEqual(reply.headers["content-type"], "image/jpeg")
        self.assertEqual(reply.content, slide_image.render_jpeg(look))


class ChallengeTests(unittest.TestCase):
    def play_card(self, web, card, answer):
        state = web.post("/api/challenge/start", json={"card": card}).json()["round"]
        web.post("/api/challenge/pick", json={"answer": answer})
        web.post("/api/challenge/reveal-ai")
        return state, web.post("/api/challenge/reveal-truth").json()["round"]

    def test_nothing_is_revealed_before_its_phase(self):
        web = client()
        state = web.post("/api/challenge/start", json={"card": "29"}).json()["round"]
        self.assertEqual(state["phase"], "choose")
        self.assertFalse({"ai_pred", "ai_probs", "ai_correct", "truth", "heatmap", "overlay"} & set(state["case"]))
        self.assertEqual(web.get("/api/challenge/image/heatmap").status_code, 404)
        self.assertEqual(web.get("/api/challenge/image/mask_overlay").status_code, 404)
        self.assertEqual(web.get("/api/challenge/image/image").status_code, 200)
        self.assertEqual(web.post("/api/challenge/reveal-ai").status_code, 409)  # no answer yet
        self.assertEqual(web.post("/api/challenge/reveal-truth").status_code, 409)
        web.post("/api/challenge/pick", json={"answer": "benign"})
        state = web.post("/api/challenge/reveal-ai").json()["round"]
        self.assertNotIn("truth", state["case"])
        self.assertEqual(state["case"]["ai_probs"], CASES["29"]["ai_probs"])
        self.assertEqual(web.get("/api/challenge/image/heatmap").status_code, 200)
        self.assertEqual(web.get("/api/challenge/image/mask_overlay").status_code, 404)
        self.assertEqual(web.post("/api/challenge/pick", json={"answer": "normal"}).status_code, 409)  # locked

    def test_every_card_matches_the_data_and_the_page_rules(self):
        web = client()
        for cid, case in CASES.items():
            _, state = self.play_card(web, str(int(cid)), "malignant")
            item = state["case"]
            self.assertEqual((item["ai_pred"], item["ai_probs"], item["truth"], item["ai_correct"]),
                             (case["ai_pred"], case["ai_probs"], case["truth"], case["correct"]), cid)
            self.assertEqual(item["explanation_key"], rules.explanation_key(case))
            self.assertEqual(item["outcome_key"], rules.outcome_key(case, "malignant"))
            self.assertEqual(item["overlap_key"], rules.overlap_label(case))
            self.assertEqual(state["score"], {"you": int(case["truth"] == "malignant"), "ai": int(case["correct"]), "played": 1})

    def test_explanations_equal_the_streamlit_page(self):
        """The page's explanation() and the API's key + values give the same sentence in both languages."""
        source = (ROOT / "pages" / "1_Challenge_Reveal.py").read_text(encoding="utf-8").replace("\nchallenge()\n", "\n")
        namespace = {}
        exec(compile(source, "page", "exec"), namespace)
        for lang in ("en", "ar"):
            text = booth.translations(lang)
            with patch.object(booth.st, "session_state", {"lang": lang}):
                for case in CASES.values():
                    api_line = text[rules.explanation_key(case)].format(
                        pred=text[case["ai_pred"]], truth=text[case["truth"]], percent=rules.explanation_percent(case))
                    self.assertEqual(api_line, namespace["explanation"](case), (lang, case["case_id"]))

    def test_round_of_five_scores_once_and_ends(self):
        web = client()
        state = web.post("/api/challenge/start", json={}).json()["round"]
        self.assertEqual(state["total"], 5)
        seen, you, ai = [], 0, 0
        for index in range(5):
            cid = f"{state['case']['card']:02d}"
            seen.append(cid)
            web.post("/api/challenge/pick", json={"answer": "benign"})
            web.post("/api/challenge/reveal-ai")
            state = web.post("/api/challenge/reveal-truth").json()["round"]
            you += CASES[cid]["truth"] == "benign"
            ai += CASES[cid]["correct"]
            self.assertEqual(state["score"], {"you": you, "ai": ai, "played": index + 1})
            self.assertEqual(web.post("/api/challenge/reveal-truth").status_code, 409)  # never scored twice
            state = web.post("/api/challenge/next").json()["round"]
        self.assertEqual(len(set(seen)), 5)
        self.assertEqual(state["phase"], "end")
        self.assertEqual(state["score"], {"you": you, "ai": ai, "played": 5})
        self.assertIsNone(web.post("/api/challenge/end").json()["round"])

    def test_card_numbers_follow_card_case_id(self):
        web = client()
        for text in ("7", "07", "#7", " 7 ", "٧"):
            self.assertEqual(web.post("/api/challenge/start", json={"card": text}).json()["round"]["case"]["card"], 7, text)
        for text in ("0", "31", "abc", "", "7.5"):
            reply = web.post("/api/challenge/start", json={"card": text})
            self.assertEqual(reply.status_code, 422, text)
            self.assertEqual(reply.json()["detail"]["code"], "card_invalid")

    def test_sessions_are_isolated(self):
        alice, bob = client(), client()
        alice.post("/api/challenge/start", json={"card": "3"})
        self.assertIsNone(bob.get("/api/challenge/round").json()["round"])
        bob.post("/api/challenge/start", json={"card": "4"})
        self.assertEqual(alice.get("/api/challenge/round").json()["round"]["case"]["card"], 3)
        alice.post("/api/chat/topic", json={"topic": "myth_fact", "lang": "en"})
        self.assertEqual(bob.get("/api/chat").json()["transcript"], [])

    def test_folders_and_scores_come_from_the_data(self):
        web = client()
        folders = web.get("/api/challenge/folders").json()
        self.assertEqual([f["id"] for f in folders], list(rules.FOLDER_CASES))
        for folder in folders:
            case = rules.folder_case(folder["id"], CASES)
            self.assertEqual((folder["ai_pred"], folder["truth"]), (case["ai_pred"], case["truth"]))
            self.assertEqual(web.get(folder["overlay"]).status_code, 200)
        self.assertEqual(web.get("/api/challenge/info").json()["scores"], booth.booth_set_scores())

    def test_the_api_never_writes_the_results_log(self):
        before = booth.RESULTS_PATH.stat().st_mtime if booth.RESULTS_PATH.exists() else None
        self.play_card(client(), "12", "normal")
        after = booth.RESULTS_PATH.stat().st_mtime if booth.RESULTS_PATH.exists() else None
        self.assertEqual(before, after)


class ChatTests(unittest.TestCase):
    def setUp(self):
        # Offline unless a test says otherwise, whatever is configured on this machine.
        self.settings = patch.object(api, "chat_settings", return_value=(None, "no secrets"))
        self.settings.start()
        self.addCleanup(self.settings.stop)

    def test_topics_are_the_hand_written_answers(self):
        web = client()
        for lang in ("en", "ar"):
            sections = chat.fallback_sections(lang)
            for topic in chat.TOPICS:
                state = web.post("/api/chat/topic", json={"topic": topic, "lang": lang}).json()
                self.assertEqual(state["transcript"][-1]["html"], chat.message_html(sections[topic]))
        self.assertEqual(web.get("/api/chat").json()["turns_left"], chat.MAX_TURNS)  # topics are not questions

    def test_offline_answers_match_the_page(self):
        web = client()
        for question in ("I found a lump in my breast", "What is a biopsy?", "عندي ألم في الثدي"):
            state = web.post("/api/chat/message", json={"question": question, "lang": "en"}).json()
            lang = "ar" if chat.is_mainly_arabic(question) else "en"
            strings = booth.translations(lang)
            notice, answer = state["transcript"][-2:]
            self.assertEqual(notice["html"], chat.message_html(strings["chat_offline"], notice=True))
            self.assertEqual(answer["html"], chat.message_html(chat.fix_numbers(chat.offline_answer(question, strings))))
        self.assertEqual(state["turns_left"], chat.MAX_TURNS - 3)
        self.assertFalse(state["live"])

    def test_limits_and_reset(self):
        web = client()
        self.assertEqual(web.post("/api/chat/message", json={"question": "  "}).json()["detail"]["code"], "chat_empty")
        too_long = web.post("/api/chat/message", json={"question": "x" * (chat.MAX_MESSAGE_CHARS + 1)})
        self.assertEqual(too_long.json()["detail"]["code"], "chat_too_long")
        for _ in range(chat.MAX_TURNS):
            self.assertEqual(web.post("/api/chat/message", json={"question": "hello"}).status_code, 200)
        limited = web.post("/api/chat/message", json={"question": "hello"})
        self.assertEqual((limited.status_code, limited.json()["detail"]["code"]), (429, "chat_turn_limit"))
        state = web.post("/api/chat/reset").json()
        self.assertEqual((state["transcript"], state["turns_left"]), ([], chat.MAX_TURNS))

    def test_live_reply_is_number_fixed_and_kept_in_history(self):
        settings = chat.Settings("deepseek", "test-key", "test-model", "https://example.invalid")
        seen = []

        def fake_call(history, lang, given):
            seen.append((list(history), lang, given))
            yield "Call "
            yield "998 in an emergency."

        self.settings.stop()
        with patch.object(api, "chat_settings", return_value=(settings, None)), \
                patch.object(api.chat, "call_llm", fake_call):
            web = client()
            web.post("/api/chat/message", json={"question": "Who do I call?", "lang": "ar"})
            state = web.post("/api/chat/message", json={"question": "Thanks", "lang": "en"}).json()
        self.settings.start()
        self.assertTrue(state["live"])
        self.assertEqual(seen[0][0], [{"role": "user", "content": "Who do I call?"}])
        self.assertEqual(seen[0][1], "ar")
        self.assertEqual(seen[1][0][1], {"role": "assistant", "content": chat.fix_numbers("Call 998 in an emergency.")})
        self.assertEqual(state["transcript"][-1]["html"], chat.message_html(chat.fix_numbers("Call 998 in an emergency.")))

    def test_a_failing_live_call_falls_back_offline(self):
        settings = chat.Settings("deepseek", "test-key", "test-model", "https://example.invalid")

        def broken(*_):
            raise chat.ChatUnavailable("timeout")
            yield  # pragma: no cover

        self.settings.stop()
        with patch.object(api, "chat_settings", return_value=(settings, None)), patch.object(api.chat, "call_llm", broken):
            state = client().post("/api/chat/message", json={"question": "I have a lump", "lang": "en"}).json()
        self.settings.start()
        self.assertEqual([entry["role"] for entry in state["transcript"]], ["user", "notice", "assistant"])

    def test_settings_read_environment_names_without_echoing_the_key(self):
        self.settings.stop()
        with patch.dict("os.environ", {"AIDA_PROVIDER": "deepseek", "AIDA_API_KEY": "secret-test-value",
                                       "AIDA_MODEL": "deepseek-chat"}):
            settings, reason = api.chat_settings()
        self.settings.start()
        self.assertIsNotNone(settings)
        self.assertIsNone(reason)
        self.assertNotIn("secret-test-value", repr(settings))


class GeneralTests(unittest.TestCase):
    def test_translations_are_the_repository_files(self):
        web = client()
        for lang in ("en", "ar"):
            self.assertEqual(web.get(f"/api/i18n/{lang}").json(), booth.translations(lang))
        self.assertEqual(web.get("/api/i18n/fr").status_code, 422)

    def test_about_numbers_come_from_metrics(self):
        metrics = json.loads((ROOT / "data" / "reports" / "metrics.json").read_text(encoding="utf-8"))
        about = client().get("/api/about").json()
        self.assertEqual((about["n_test"], about["accuracy"], about["caught"], about["missed"], about["false_alarms"]),
                         (metrics["n_test"], metrics["accuracy"], metrics["malignant_caught"],
                          metrics["malignant_missed"], metrics["false_alarms"]))
        self.assertEqual(about["confusion_matrix"], metrics["confusion_matrix"])
        for url in about["images"].values():
            self.assertEqual(client().get(url).status_code, 200)

    def test_home_cards_are_booth_originals(self):
        web = client()
        for url in web.get("/api/home").json()["cards"]:
            self.assertEqual(web.get(url).status_code, 200)
        self.assertEqual(web.get("/api/cards/99/original").status_code, 404)


if __name__ == "__main__":
    unittest.main()
