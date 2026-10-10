"""Cloud configuration, safe fallbacks and direction. No test contacts a provider."""
import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx2 as httpx
from openai import APIConnectionError, APITimeoutError, AuthenticationError
from streamlit.errors import StreamlitSecretNotFoundError
from streamlit.testing.v1 import AppTest

import aida_chat as chat
from booth import translations
from test_chat import FAKE, fake_client

ROOT = Path(__file__).resolve().parents[1]


class CloudSettingsTests(unittest.TestCase):
    def test_flat_layout_matches_local_key_structure(self):
        # A synthetic key only: never open local secrets from a test.
        settings = chat.settings_from({"PROVIDER": "deepseek", "API_KEY": "test-key", "MODEL": "deepseek-chat"})
        self.assertEqual(settings.base_url, chat.BASE_URLS["deepseek"])
        self.assertEqual(settings.model, "deepseek-chat")
        self.assertNotIn("test-key", repr(settings))

    def test_missing_configuration_categories(self):
        for config, expected in ((None, "no secrets"), ({}, "no secrets"),
                                 ({"MODEL": "m"}, "missing API_KEY"),
                                 ({"API_KEY": None}, "missing API_KEY"),
                                 ({"API_KEY": "PASTE_YOUR_KEY_HERE"}, "missing API_KEY"),
                                 ({"API_KEY": "test-key", "PROVIDER": "deepseek"}, "missing MODEL/BASE_URL"),
                                 ({"API_KEY": "test-key", "MODEL": "m"}, "missing MODEL/BASE_URL")):
            self.assertEqual(chat.configuration_reason(config), expected)
        self.assertIsNone(chat.configuration_reason({"PROVIDER": "deepseek", "API_KEY": "test-key", "MODEL": "m"}))

    def test_missing_streamlit_file_category(self):
        class MissingSecrets(dict):
            def __bool__(self):
                raise StreamlitSecretNotFoundError("private path")
        self.assertEqual(chat.configuration_reason(MissingSecrets()), "no secrets")

    def test_sdk_errors_are_safe_categories(self):
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(401, request=request)
        private = "private-key and private-user-message"
        errors = [(AuthenticationError(private, response=response, body=None), "auth error (401)"),
                  (APITimeoutError(request=request), "timeout"),
                  (APIConnectionError(message=private, request=request), "network"),
                  (ValueError(private), "ValueError")]
        for error, category in errors:
            with self.assertRaises(chat.ChatUnavailable) as raised:
                list(chat.call_llm([], "en", FAKE, "S", fake_client(error=error)))
            self.assertEqual(str(raised.exception), category)
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                chat.log_fallback(str(raised.exception))
            self.assertEqual(output.getvalue(), category + "\n")
            self.assertNotIn(private, output.getvalue())

    def test_client_construction_failures_are_categorized(self):
        with patch("openai.OpenAI", side_effect=ValueError("private-key")):
            with self.assertRaisesRegex(chat.ChatUnavailable, "^ValueError$"):
                list(chat.call_llm([], "en", FAKE, "S"))

    def test_daily_cap_category(self):
        with patch.object(chat, "take_daily_call", return_value=False):
            with self.assertRaisesRegex(chat.ChatUnavailable, "^daily cap$"):
                list(chat.call_llm([], "en", FAKE, "S"))

    def test_diagnostic_rejects_arbitrary_messages(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            chat.log_fallback("private key: private-user-message\nsecond line")
        self.assertEqual(output.getvalue(), "ChatUnavailable\n")


class OfflineRoutingTests(unittest.TestCase):
    def test_man_with_lump_arabic(self):
        question = "ماذا افعل انا رجل واحس بورم في صدري"
        answer = chat.offline_answer(question, translations("ar"))
        exact = "يُرجى مراجعة الطبيب قريبًا بشأن أي تغيّر جديد. معظم الكتل ليست سرطانية، لكن الطبيب وحده يستطيع التأكد. يمكن أن يُصاب الرجال بسرطان الثدي أيضًا. وفي الحالات الطارئة اتصلوا بالرقم 998."
        self.assertEqual(answer, exact + "\n\n" + chat.fallback_sections("ar")["know_signs"])

    def test_man_with_lump_english(self):
        answer = chat.offline_answer("I am a man and feel a lump in my chest. What should I do?", translations("en"))
        exact = "Please see a doctor soon about any new change. Most lumps are not cancer, but only a doctor can check. Men can get breast cancer too. In an emergency call 998."
        self.assertEqual(answer, exact + "\n\n" + chat.fallback_sections("en")["know_signs"])

    def test_generic_question_has_no_random_section(self):
        for lang, question in (("en", "What can you help with?"), ("ar", "ما المعلومات التي يمكنكم تقديمها؟")):
            answer = chat.offline_answer(question, translations(lang))
            self.assertEqual(answer, translations(lang)["chat_offline_generic"])
            self.assertIn("998", answer)
            for section in chat.fallback_sections(lang).values():
                self.assertNotIn(section, answer)

    def test_symptom_variants_override_myth_and_help_words(self):
        for symptom in ("swelling", "pain", "discharge", "nipple", "skin change", "tumour",
                        "ورم", "كتلة", "تورم", "ألم", "الألم", "إفرازات", "حلمة", "جلد", "وَرَم"):
            self.assertTrue(chat.mentions_symptom(f"man doctor myth رجل طبيب {symptom}"), symptom)


class DirectionTests(unittest.TestCase):
    def test_arabic_letters_win_over_digits_and_punctuation(self):
        for text in ("ماذا افعل انا رجل واحس بورم في صدري", "«مرحبًا بكم» 998!",
                     "اتصلوا https://example.test/very-long-english-url", "ﻣﺮﺣﺒﺎ"):
            self.assertTrue(chat.is_mainly_arabic(text), text)

    def test_english_majority_empty_numbers_and_tie_are_ltr(self):
        for text in ("English question with a small Arabic word مرحبا", "", "998 +971 6", "aب", "؟"):
            self.assertFalse(chat.is_mainly_arabic(text), text)

    def test_directional_lists_and_unsafe_html(self):
        arabic = chat.message_html("علامات:\n\n- كتلة\n- ألم")
        self.assertIn('dir="rtl"', arabic)
        self.assertIn('<ul dir="rtl">', arabic)
        self.assertIn('<li dir="rtl">', arabic)
        self.assertIn('text-align:right', arabic)
        english = chat.message_html('Hello <script>alert("private")</script> [bad](javascript:alert(1))')
        self.assertIn('dir="ltr"', english)
        self.assertNotIn('<script>', english)
        self.assertNotIn('href="javascript:', english)


class CrossLanguagePageTests(unittest.TestCase):
    def page(self, lang):
        app = AppTest.from_file(str(ROOT / "public_app.py"), default_timeout=15).run()
        app.radio(key="language_choice").set_value(lang).run()
        return app.switch_page("pages/3_Ask_AIDA.py").run()

    def test_response_and_direction_follow_question_not_ui(self):
        with patch.object(chat, "settings_from", return_value=None):
            for ui, lang, question in (("en", "ar", "ماذا افعل انا رجل واحس بورم في صدري"),
                                       ("ar", "en", "I am a man and feel a lump in my chest")):
                app = self.page(ui)
                app.chat_input(key="chat_question").set_value(question).run()
                self.assertFalse(app.exception)
                saved = app.session_state["chat_history"][-1]["content"]
                self.assertIn(translations(lang)["chat_symptom_guidance"].split("998")[0], saved)
                html = [entry.proto.body for entry in app.get("html")]
                self.assertIn(chat.message_html(question), html)
                self.assertIn(chat.message_html(translations(lang)["chat_offline"], notice=True), html)
                # A rerun also wraps messages replayed from history.
                app.run()
                self.assertIn(chat.message_html(saved), [entry.proto.body for entry in app.get("html")])

    def test_quick_button_answers_remain_unchanged(self):
        with patch.object(chat, "settings_from", return_value=None):
            for lang in ("en", "ar"):
                app = self.page(lang)
                for topic in chat.TOPICS:
                    app.button(key=topic).click().run()
                    self.assertFalse(app.exception)
                    self.assertIn(chat.fallback_sections(lang)[topic], [entry.value for entry in app.markdown])

    def test_fallback_logs_once_and_reruns_do_not_log(self):
        with patch.object(chat, "settings_from", return_value=FAKE):
            app = self.page("en")
            with patch.object(chat, "call_llm", side_effect=chat.ChatUnavailable("auth error (401)")), \
                    patch.object(chat, "log_fallback", wraps=chat.log_fallback) as log:
                app.chat_input(key="chat_question").set_value("A private question").run()
                self.assertFalse(app.exception)
                log.assert_called_once_with("auth error (401)")
                app.run()
                log.assert_called_once()
