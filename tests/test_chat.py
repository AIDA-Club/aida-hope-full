"""Ask AIDA tests. No test ever calls a real API: settings are patched to None or a fake client is used."""
import importlib.util
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import aida_chat as chat
import booth

ROOT = Path(__file__).resolve().parents[1]
FAKE = chat.Settings("deepseek", "test-key", "test-model", chat.BASE_URLS["deepseek"])


def fake_client(pieces=None, error=None):
    """A stand-in for openai.OpenAI that streams the given text pieces or raises."""
    def create(**kwargs):
        fake_client.last_kwargs = kwargs
        if error:
            raise error
        return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))])
                for piece in pieces]
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


class ChatLogicTests(unittest.TestCase):
    def test_no_key_means_offline(self):
        for secrets in (None, {}, {"PROVIDER": "deepseek", "API_KEY": "", "MODEL": "m"},
                        {"PROVIDER": "deepseek", "API_KEY": "PASTE_YOUR_KEY_HERE", "MODEL": "m"},
                        {"PROVIDER": "unknown", "API_KEY": "k", "MODEL": "m"}):
            self.assertIsNone(chat.settings_from(secrets), secrets)
        with self.assertRaises(chat.ChatUnavailable):
            list(chat.call_llm([{"role": "user", "content": "hi"}], "en", None))

    def test_provider_base_urls(self):
        gemini = chat.settings_from({"PROVIDER": "gemini", "API_KEY": "k", "MODEL": "m"})
        self.assertEqual(gemini.base_url, "https://generativelanguage.googleapis.com/v1beta/openai/")
        custom = chat.settings_from({"PROVIDER": "deepseek", "API_KEY": "k", "MODEL": "m", "BASE_URL": "https://x.test"})
        self.assertEqual(custom.base_url, "https://x.test")

    def test_message_length_limit(self):
        self.assertIsNone(chat.check_message("a" * chat.MAX_MESSAGE_CHARS))
        self.assertEqual(chat.check_message("a" * (chat.MAX_MESSAGE_CHARS + 1)), "chat_too_long")
        self.assertEqual(chat.check_message("   "), "chat_empty")

    def test_turn_limit(self):
        history = []
        for _ in range(chat.MAX_TURNS):
            history += [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
        self.assertEqual(chat.turns_left(history), 0)
        self.assertEqual(chat.turns_left(history[:-2]), 1)

    def test_streaming_and_request_limits(self):
        client = fake_client(["Hello", " there"])
        reply = "".join(chat.call_llm([{"role": "user", "content": "hi"}], "ar", FAKE, "SYSTEM", client))
        self.assertEqual(reply, "Hello there")
        kwargs = fake_client.last_kwargs
        self.assertEqual(kwargs["max_tokens"], 400)
        self.assertTrue(kwargs["stream"])
        self.assertIn("Arabic", kwargs["messages"][0]["content"])

    def test_api_error_becomes_unavailable(self):
        with self.assertRaises(chat.ChatUnavailable):
            list(chat.call_llm([{"role": "user", "content": "hi"}], "en", FAKE, "S",
                               fake_client(error=TimeoutError("slow"))))

    def test_context_excludes_fallbacks(self):
        prompt = chat.build_system_prompt()
        self.assertTrue(prompt.startswith("You are AIDA"))
        for name in ("signs.md", "risk.md", "myths.md", "terms.md", "screening.md", "help_uae.md",
                     "about_booth.md"):
            self.assertIn(f"--- {name} ---", prompt)
        self.assertNotIn("fallback_", prompt)

    def test_fallback_topics_and_routing(self):
        for lang in ("en", "ar"):
            self.assertEqual(set(chat.fallback_sections(lang)), set(chat.TOPICS))
        self.assertEqual(chat.match_topic("I found a lump"), "know_signs")
        self.assertEqual(chat.match_topic("what does biopsy mean"), "explain_term")
        self.assertEqual(chat.match_topic("hello"), "get_help")

    def test_secrets_toml_is_git_ignored(self):
        patterns = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".streamlit/secrets.toml", [line.strip() for line in patterns])
        try:
            result = subprocess.run(["git", "check-ignore", "-q", ".streamlit/secrets.toml"], cwd=ROOT,
                                    capture_output=True)
        except FileNotFoundError:
            return  # git not installed: the .gitignore line check above still applies
        if result.returncode != 128:  # 128 = not a git repository
            self.assertEqual(result.returncode, 0, "secrets.toml is not ignored by git")

    def test_eval_flags_phone_numbers_and_doses(self):
        spec = importlib.util.spec_from_file_location("eval_chat", ROOT / "scripts" / "eval_chat.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.flag_answer("Call +971 6 123 4567"))
        self.assertTrue(module.flag_answer("take 20 mg a day"))
        self.assertTrue(module.flag_answer("خذ ٢٠ ملغ"))
        self.assertEqual(module.flag_answer("About 0.5–1% of cases; ages 50–69; 2.4 million in 2024."), [])


class AskPageTests(unittest.TestCase):
    def setUp(self):
        # Never reach a real provider from tests, even if secrets.toml exists.
        patcher = patch.object(chat, "settings_from", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def page(self, lang="en"):
        app = AppTest.from_file(str(ROOT / "Home.py"), default_timeout=15).run()
        app.radio(key="language_choice").set_value(lang).run()
        app.switch_page("pages/3_Ask_AIDA.py").run()
        self.assertFalse(app.exception)
        return app

    def test_fallback_with_no_key(self):
        for lang, question in (("en", "I found a lump, do I have cancer?"), ("ar", "ما هي علامات سرطان الثدي؟")):
            app = self.page(lang)
            self.assertIn(booth.translations(lang)["chat_disclaimer"], [w.value for w in app.warning])
            app.chat_input(key="chat_question").set_value(question).run()
            self.assertFalse(app.exception)
            self.assertIn(booth.translations(lang)["chat_offline"], [i.value for i in app.info])
            self.assertTrue(any("cancer.gov/types/breast/symptoms" in m.value for m in app.markdown))
            self.assertEqual(len(app.session_state["chat_history"]), 2)

    def test_long_message_rejected(self):
        app = self.page()
        app.chat_input(key="chat_question").set_value("x" * (chat.MAX_MESSAGE_CHARS + 1)).run()
        self.assertTrue(app.error)
        self.assertEqual(app.session_state["chat_history"], [])

    def test_turn_limit_disables_input(self):
        app = self.page()
        app.session_state["chat_history"] = [{"role": role, "content": "x"} for _ in range(chat.MAX_TURNS)
                                             for role in ("user", "assistant")]
        app.run()
        self.assertTrue(app.chat_input(key="chat_question").disabled)
        self.assertIn(booth.translations("en")["chat_turn_limit"], [i.value for i in app.info])


if __name__ == "__main__":
    unittest.main()
