"""Ask AIDA tests. No test ever calls a real API: settings are patched to None or a fake client is used."""
import importlib.util
import subprocess
import tempfile
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

    def test_eval_flags_mixed_address(self):
        spec = importlib.util.spec_from_file_location("eval_chat", ROOT / "scripts" / "eval_chat.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mixed = "أتفهّم خوفك، لا أستطيع أن أخبرك. لا تنتظروا، بل احجزوا موعداً."
        self.assertTrue(module.flag_mixed_address(mixed))
        self.assertTrue(module.flag_mixed_address("احجزي موعداً، واسألوا طبيبكم."))
        self.assertEqual(module.flag_mixed_address("راجعوا الطبيب قريباً، واسألوا طبيبكم. كم حالة؟ يتم الحجز."), [])
        self.assertEqual(module.flag_mixed_address("أتفهّم خوفكِ، احجزي موعداً مع طبيبتك."), [])

    def test_eval_flags_arabic_slips(self):
        spec = importlib.util.spec_from_file_location("eval_chat", ROOT / "scripts" / "eval_chat.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.flag_arabic("تغطي فحص وتreatment سرطان الثدي"))
        self.assertTrue(module.flag_arabic("جامعة عاجمان"))
        self.assertTrue(module.flag_arabic("هاتف 6 7056294"))
        clean = ("صحة (SEHA) ‎80050 (seha.ae)، مبنى Student Hub، Counseling@ajman.ac.ae، "
                 "https://www.focp.ae/ الهاتف ‎+971 6 506 5542 أو 067056813، الإسعاف 998")
        self.assertEqual(module.flag_arabic(clean), [])


class KnowledgeBaseTests(unittest.TestCase):
    KB_FILES = ("signs.md", "risk.md", "myths.md", "terms.md", "screening.md", "help_uae.md",
                "about_booth.md", "fallback_en.md", "fallback_ar.md", "system_prompt.md")

    def test_kb_files_exist_and_are_not_empty(self):
        for name in self.KB_FILES:
            path = chat.KB / name
            self.assertTrue(path.is_file(), name)
            self.assertTrue(path.read_text(encoding="utf-8").strip(), name)

    def test_fallbacks_have_exactly_the_four_headings(self):
        for lang in ("en", "ar"):
            text = (chat.KB / f"fallback_{lang}.md").read_text(encoding="utf-8")
            headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
            self.assertEqual(headings, list(chat.FALLBACK_HEADINGS), lang)
            sections = chat.fallback_sections(lang)
            self.assertEqual(list(sections), list(chat.TOPICS), lang)
            self.assertTrue(all(sections.values()), lang)

    def test_prompt_hides_unconfirmed_contacts(self):
        prompt = chat.build_system_prompt()
        for hidden in ("## Not yet confirmed", "800 8877", "80011111", "Marsa Ajman",
                       "info@pinkcaravan.ae", "Sakina"):
            self.assertNotIn(hidden, prompt)
        for shown in ("998", "+971 6 506 5542", "80050"):
            self.assertIn(shown, prompt)
        self.assertIn("CONFIRMED sections of help_uae.md", prompt)
        # The full list stays on disk for the booth team.
        self.assertIn("Marsa Ajman", (chat.KB / "help_uae.md").read_text(encoding="utf-8"))

    def test_strip_unconfirmed(self):
        text = "keep 1\n\n---\n\n## Not yet confirmed\nsecret\n\n## Sources\n- a"
        self.assertEqual(chat.strip_unconfirmed(text), "keep 1\n\n## Sources\n- a")
        self.assertEqual(chat.strip_unconfirmed("a\n## Not yet confirmed\nsecret"), "a")
        self.assertEqual(chat.strip_unconfirmed("nothing to cut"), "nothing to cut")

    def test_prompt_size_under_cap(self):
        self.assertLess(len(chat.build_system_prompt()), chat.MAX_SYSTEM_PROMPT_CHARS)

    def test_prompt_drops_help_sources_only(self):
        # risk.md keeps its Sources, which cite one Gulf News article for a UAE statistic.
        # That exact URL is allowed; no other news link may reach the prompt.
        allowed = "https://gulfnews.com/uae/health/uae-breast-cancer-rate-hits-94-per-100000-women-1.500330567"
        prompt = chat.build_system_prompt()
        for link in ("gulfnews.com", "sharjah24.ae", "emirates247.com"):
            self.assertNotIn(link, prompt.replace(allowed, ""))
        help_part = prompt.split("--- help_uae.md ---")[1].split("\n--- ")[0]
        self.assertNotIn("## Sources", help_part)
        for name in ("signs.md", "risk.md", "myths.md", "terms.md", "screening.md", "about_booth.md"):
            part = prompt.split(f"--- {name} ---")[1].split("\n--- ")[0]
            self.assertIn("## Sources", part, name)

    def test_arabic_answer_rules(self):
        system = (chat.KB / "system_prompt.md").read_text(encoding="utf-8")
        self.assertIn("Arabic answers:", system)
        for rule in ("Write Arabic answers fully in Arabic", "Copy phone numbers EXACTLY",
                     "plural/neutral form", "official Arabic names from the list in help_uae.md",
                     "keep that same form for the whole reply", "Never mix singular and",
                     "Never add services, coverage or details",
                     "Don't name or translate a programme"):
            self.assertIn(rule, system)
        self.assertIn("Arabic answers:", chat.build_system_prompt())

    def test_arabic_names_survive_confirmed_help(self):
        text = chat.confirmed_help((chat.KB / "help_uae.md").read_text(encoding="utf-8"))
        self.assertIn("## Official Arabic names", text)
        self.assertIn("<!-- AR names: native review -->", text)
        for name in ("مركز أبوظبي للصحة العامة", "هيئة الصحة بدبي", "جمعية أصدقاء مرضى السرطان",
                     "شركة أبوظبي للخدمات الصحية (صحة)", "مبنى Student Hub",
                     "مقدّمو الخدمة المعتمدون لدى مركز أبوظبي للصحة العامة"):
            self.assertIn(name, text)
        self.assertIn("مركز أبوظبي للصحة العامة", chat.build_system_prompt())

    def test_fallback_ar_uses_neutral_address(self):
        text = (chat.KB / "fallback_ar.md").read_text(encoding="utf-8")
        for feminine in ("انتبهي", "اسأليني", "سمعتِ", "لاحظتِ"):
            self.assertNotIn(feminine, text)

    def test_fix_reversed_numbers(self):
        iso = (chat.LTR_ISOLATE, chat.POP_ISOLATE)
        fixed = chat.fix_numbers("هاتف 6294 705 6 971+، من 9 صباحاً")
        self.assertEqual(fixed, f"هاتف {iso[0]}+971 6 7056294{iso[1]}، من 9 صباحاً")
        self.assertIn("+971 6 506 5542", chat.fix_numbers("اتصلوا على 5542 506 6 971+"))
        self.assertIn("+971 6 506 5542", chat.fix_numbers("اتصلوا على 2455 605 6 179"))  # every digit reversed
        self.assertEqual(chat.number_fixes("هاتف 6294 705 6 971+"), [("6294 705 6 971+", "+971 6 7056294")])

    def test_fix_numbers_leaves_the_rest_alone(self):
        english = "Call 998 in an emergency, or SEHA on 80050. In 2024, 21 of 24 were caught."
        self.assertEqual(chat.fix_numbers(english), english)
        arabic = chat.fix_numbers("اتصلوا بـ 998 أو صحة 80050")
        self.assertIn(f"{chat.LTR_ISOLATE}998{chat.POP_ISOLATE}", arabic)
        self.assertIn(f"{chat.LTR_ISOLATE}80050{chat.POP_ISOLATE}", arabic)
        self.assertEqual(chat.fix_numbers("رقم 050 123 4567 غير مؤكد"), "رقم 050 123 4567 غير مؤكد")
        once = chat.fix_numbers("هاتف 6294 705 6 971+")
        self.assertEqual(chat.fix_numbers(once), once)  # running it twice changes nothing

    def test_confirmed_numbers_come_from_confirmed_part_only(self):
        numbers = chat.confirmed_numbers()
        for digits in ("97165065542", "80050", "97167056294", "998", "999", "997"):
            self.assertIn(digits, numbers)
        for hidden in ("8008877", "80011111", "800725462"):  # all in "Not yet confirmed"
            self.assertNotIn(hidden, numbers)
        self.assertNotIn("77881", numbers)  # the FOCP PO Box is not a phone number

    def test_strip_section(self):
        text = "# T\n## A\na\n## Sources\n- x\n## B\nb"
        self.assertEqual(chat.strip_section(text, "## Sources"), "# T\n## A\na\n## B\nb")
        self.assertEqual(chat.strip_section("no heading", "## Sources"), "no heading")


class PublicExportTests(unittest.TestCase):
    def export(self):
        spec = importlib.util.spec_from_file_location("export_public", ROOT / "scripts" / "export_public.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        dest = Path(temp.name) / "public_deploy"
        return dest, module.export(dest)

    def test_public_help_file_is_confirmed_only(self):
        dest, _ = self.export()
        text = (dest / "kb" / "help_uae.md").read_text(encoding="utf-8")
        for shown in ("+971 6 506 5542", "80050"):
            self.assertIn(shown, text)
        for hidden in ("## Not yet confirmed", "Marsa Ajman", "800 8877", "gulfnews.com"):
            self.assertNotIn(hidden, text)

    def test_export_skips_private_files(self):
        _, copied = self.export()
        for name in copied:
            for private in ("docs/", "booth_set", "results.csv", "1_Challenge", "2_Tweak", "secrets.toml"):
                if name != ".streamlit/secrets.example.toml":
                    self.assertNotIn(private, name)
        self.assertEqual([name for name in copied if name.startswith("data/")],
                         ["data/reports/confusion_matrix.png", "data/reports/metrics.json"])


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
            expected = chat.fix_numbers(chat.fallback_sections(lang)[chat.match_topic(question)])
            self.assertIn(expected, [m.value for m in app.markdown])
            self.assertEqual(len(app.session_state["chat_history"]), 2)

    def test_live_reply_numbers_fixed_on_screen_and_in_history(self):
        reply = "اتصلوا بالعيادة على 6294 705 6 971+ قريباً."
        app = self.page("ar")
        with patch.object(chat, "settings_from", return_value=FAKE), \
                patch.object(chat, "call_llm", side_effect=lambda *args, **kwargs: iter([reply])):
            app.chat_input(key="chat_question").set_value("ما رقم العيادة؟").run()
        self.assertFalse(app.exception)
        saved = app.session_state["chat_history"][-1]["content"]
        self.assertEqual(saved, chat.fix_numbers(reply))
        self.assertIn(f"{chat.LTR_ISOLATE}+971 6 7056294{chat.POP_ISOLATE}", saved)
        self.assertIn(saved, [m.value for m in app.markdown])

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
