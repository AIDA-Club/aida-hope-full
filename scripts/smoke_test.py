"""Headless smoke test of every page, in English and Arabic. Requires playwright and local Chrome.

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\smoke_test.py

- Starts its own headless Streamlit server on port 8503.
- Uses a temporary results CSV, so data/results.csv is never touched.
- Forces Ask AIDA offline (no API key), so nothing is sent anywhere.
- Saves screenshots and a summary to smoke_out/ (git-ignored).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "smoke_out"
PORT = 8503
URL = f"http://127.0.0.1:{PORT}"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
sys.path.insert(0, str(ROOT))
from booth import translations  # noqa: E402

# The server: temporary results CSV + Ask AIDA forced offline.
WRAPPER = ("import sys; from pathlib import Path; import booth, aida_chat; "
           "booth.RESULTS_PATH = Path(sys.argv[1]); aida_chat.settings_from = lambda secrets: None; "
           "from streamlit.web import cli; sys.argv = ['streamlit', 'run', sys.argv[2], "
           f"'--server.headless', 'true', '--server.address', '127.0.0.1', '--server.port', '{PORT}']; "
           "cli.main()")


def wait_for_server(server: subprocess.Popen) -> None:
    for _ in range(150):
        if server.poll() is not None:
            raise RuntimeError("The smoke-test server exited before startup.")
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("The smoke-test server did not start.")


def check_page(page, name: str, lang: str, results: dict) -> None:
    """No Streamlit exception, the right text direction, the footer, then a screenshot."""
    page.wait_for_timeout(600)
    # The footer is drawn last (after the page script finishes), so wait for it rather
    # than trusting a fixed pause: the Tweak page loads its model first and can be slow.
    try:
        page.locator(".booth-footer").first.wait_for(timeout=15000)
    except Exception:
        pass  # the assert below reports it
    assert page.locator('[data-testid="stException"]').count() == 0, f"{name}: exception on page"
    direction = page.evaluate("getComputedStyle(document.querySelector('.stApp')).direction")
    assert direction == ("rtl" if lang == "ar" else "ltr"), f"{name}: direction {direction}"
    assert page.locator(".booth-footer").count() == 1, f"{name}: footer missing"
    page.screenshot(path=str(OUTPUT / f"{name}.png"), full_page=True)
    results[name] = f"ok ({direction})"


def nav(page, title: str) -> None:
    page.locator('[data-testid="stSidebarNav"]').get_by_role("link", name=title, exact=True).click()
    page.wait_for_timeout(800)


def play_round(page, text: dict, case_id: str, first: str) -> None:
    entry = page.locator(".st-key-case_number input")
    entry.wait_for()
    entry.fill(case_id)
    entry.press("Enter")
    for key in (f"first_{first}", "reveal_ai", "keep_answer", "reveal_truth"):
        button = page.locator(f".st-key-{key} button")
        button.wait_for()
        page.wait_for_function("s => !document.querySelector(s).disabled", arg=f".st-key-{key} button")
        button.click()
    page.locator(".booth-learn").filter(has_text=text["learn_line"]).wait_for()
    assert page.get_by_text(text["learn_heading"], exact=True).count() == 1


def check_cross_language_chat(page, ui_lang: str, results: dict) -> None:
    """Both new bubbles and the offline notice follow the message, including lists."""
    original_viewport = page.viewport_size
    page.set_viewport_size({"width": 1600, "height": 1800})
    reply_lang = "ar" if ui_lang == "en" else "en"
    question = ("ماذا افعل انا رجل واحس بورم في صدري" if reply_lang == "ar"
                else "I am a man and feel a lump in my chest. What should I do?")
    text = translations(reply_lang)
    box = page.locator('[data-testid="stChatInputTextArea"]')
    box.fill(question)
    box.press("Enter")
    messages = page.locator('[data-testid="stChatMessage"]')
    assistant = messages.last
    assistant.get_by_text(text["chat_symptom_guidance"].split("998")[0], exact=False).wait_for()
    direction, align = ("rtl", "right") if reply_lang == "ar" else ("ltr", "left")
    for message in (messages.nth(messages.count() - 2), assistant):
        for container in message.locator(".aida-message").all():
            assert container.get_attribute("dir") == direction
            actual = container.evaluate("e => [getComputedStyle(e).direction, getComputedStyle(e).textAlign]")
            assert actual == [direction, align], f"chat container: {actual}"
    assert assistant.locator(".aida-offline-notice").get_attribute("dir") == direction
    lists = assistant.locator(".aida-message ul, .aida-message ol")
    assert lists.count() > 0, "Signs answer lost its lists"
    for listing in lists.all():
        assert listing.get_attribute("dir") == direction
        assert listing.evaluate("e => getComputedStyle(e).direction") == direction
        for item in listing.locator("li").all():
            assert item.evaluate("e => getComputedStyle(e).textAlign") == align
    name = f"{ui_lang}_ui_{reply_lang}_message"
    # Streamlit scrolls its own main panel; include both the question and reply.
    messages.nth(messages.count() - 2).evaluate("e => e.scrollIntoView({block:'start'})")
    check_page(page, name, ui_lang, results)
    page.set_viewport_size(original_viewport)


def run_language(page, lang: str, results: dict) -> None:
    text = translations(lang)
    page.goto(URL)
    page.locator('[data-testid="stSidebarNav"]').wait_for()
    if lang == "ar":
        page.locator('[data-testid="stSidebar"]').get_by_text("العربية", exact=True).click()
        page.wait_for_timeout(1000)
    check_page(page, f"{lang}_home", lang, results)

    nav(page, text["challenge_title"])
    case_id, first = ("02", "normal") if lang == "en" else ("17", "benign")  # a normal case / an AI error
    play_round(page, text, case_id, first)
    if lang == "ar":
        assert page.get_by_text(text["ai_error_note"], exact=True).count() == 1
    check_page(page, f"{lang}_challenge_case{case_id}", lang, results)
    page.locator(".st-key-next_visitor button").click()

    nav(page, text["tweak_title"])
    check_page(page, f"{lang}_tweak", lang, results)

    nav(page, text["ask_title"])
    page.locator(".st-key-know_signs button").click()
    page.wait_for_timeout(500)
    question = "I found a lump, do I have cancer?" if lang == "en" else "وجدت كتلة، هل هذا سرطان؟"
    box = page.locator('[data-testid="stChatInputTextArea"]')
    box.fill(question)
    box.press("Enter")
    page.get_by_text(text["chat_offline"], exact=True).first.wait_for()
    assert page.get_by_text(text["chat_disclaimer"], exact=True).count() == 1
    check_page(page, f"{lang}_ask_no_key", lang, results)
    check_cross_language_chat(page, lang, results)

    nav(page, text["about_title"])
    page.locator('[data-testid="stMetric"]').first.wait_for()
    check_page(page, f"{lang}_about", lang, results)


def main() -> int:
    OUTPUT.mkdir(exist_ok=True)
    results: dict = {}
    with tempfile.TemporaryDirectory() as temporary, (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, "-c", WRAPPER, str(Path(temporary) / "results.csv"),
                                   str(ROOT / "Home.py")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_for_server(server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
                page = browser.new_page(viewport={"width": 1600, "height": 1000})
                page.on("pageerror", lambda error: results.setdefault("browser_errors", []).append(str(error)))
                page.set_default_timeout(20000)
                for lang in ("en", "ar"):
                    run_language(page, lang, results)
                # Phone-sized check of Ask AIDA (visitors open it from the QR code).
                phone = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
                phone.goto(f"{URL}/ask")
                phone.locator('[data-testid="stChatInputTextArea"]').wait_for()
                overflow = phone.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                assert not overflow, "Ask AIDA scrolls sideways on a phone"
                check_page(phone, "phone_ask", "en", results)
                assert not results.get("browser_errors"), "Browser reported a JavaScript error"
                browser.close()
            results["status"] = "PASS"
        except Exception as exc:  # report and keep the summary
            results["status"] = f"FAIL: {exc}"
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
    (OUTPUT / "smoke_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
