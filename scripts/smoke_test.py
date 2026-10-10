"""Headless smoke test of every page, in English and Arabic. Requires playwright and local Chrome.

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\smoke_test.py [--public-python PATH]

- Booth: starts its own headless Streamlit server (Home.py) on port 8503, with a temporary
  results CSV, so data/results.csv is never touched.
- Public website: then serves public_deploy/public_app.py on port 8505 (run
  scripts/export_public.py first) at phone size, 375 x 812, and plays both Challenge modes,
  Tweak the Tumor, Ask AIDA and About in English and Arabic. --public-python runs that server
  with another interpreter, e.g. a fresh venv built only from public_deploy/requirements.txt.
  It fails if any file in public_deploy/ is created or changed while visitors play.
- Forces Ask AIDA offline (no API key), so nothing is sent anywhere.
- Saves screenshots and a summary to smoke_out/ (git-ignored); the public ones in smoke_out/public/.
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
PUBLIC_DIR = ROOT / "public_deploy"
PUBLIC_PORT = 8505
PUBLIC_URL = f"http://127.0.0.1:{PUBLIC_PORT}"
PHONE = {"width": 375, "height": 812}
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
sys.path.insert(0, str(ROOT))
from booth import translations  # noqa: E402

# The server: temporary results CSV + Ask AIDA forced offline.
WRAPPER = ("import sys; from pathlib import Path; import booth, aida_chat; "
           "booth.RESULTS_PATH = Path(sys.argv[1]); aida_chat.settings_from = lambda secrets: None; "
           "from streamlit.web import cli; sys.argv = ['streamlit', 'run', sys.argv[2], "
           f"'--server.headless', 'true', '--server.address', '127.0.0.1', '--server.port', '{PORT}']; "
           "cli.main()")
# The public server: run from public_deploy/ with Ask AIDA forced offline (nothing else patched).
PUBLIC_WRAPPER = ("import sys; import aida_chat; aida_chat.settings_from = lambda secrets: None; "
                  "from streamlit.web import cli; sys.argv = ['streamlit', 'run', 'public_app.py', "
                  "'--server.headless', 'true', '--server.address', '127.0.0.1', "
                  f"'--server.port', '{PUBLIC_PORT}', '--browser.gatherUsageStats', 'false']; cli.main()")


def wait_for_server(server: subprocess.Popen, url: str = URL) -> None:
    for _ in range(300):
        if server.poll() is not None:
            raise RuntimeError("The smoke-test server exited before startup.")
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("The smoke-test server did not start.")


def check_page(page, name: str, lang: str, results: dict, folder: Path = OUTPUT) -> None:
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
    page.screenshot(path=str(folder / f"{name}.png"), full_page=True)
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


# ---------------------------------------------------------------------------
# Public website, phone size
# ---------------------------------------------------------------------------
def tap(page, key: str) -> None:
    button = page.locator(f".st-key-{key} button")
    button.wait_for()
    page.wait_for_function("s => !document.querySelector(s).disabled", arg=f".st-key-{key} button")
    button.click()
    page.wait_for_timeout(300)


def open_sidebar(page) -> None:
    if page.locator('[data-testid="stSidebar"]').get_attribute("aria-expanded") != "true":
        page.locator('[data-testid="stExpandSidebarButton"], '
                     '[data-testid="stSidebarCollapsedControl"] button').first.click()
        page.wait_for_timeout(600)


def close_sidebar(page) -> None:
    if page.locator('[data-testid="stSidebar"]').get_attribute("aria-expanded") == "true":
        page.locator('[data-testid="stSidebarCollapseButton"] button, '
                     '[data-testid="stSidebarHeader"] button').first.click()
        page.wait_for_timeout(500)


def phone_nav(page, title: str) -> None:
    open_sidebar(page)
    page.locator('[data-testid="stSidebarNav"]').get_by_role("link", name=title, exact=True).click()
    page.wait_for_timeout(1000)
    close_sidebar(page)


def check_phone(page, name: str, lang: str, results: dict, folder: Path) -> None:
    """Checks at 375 x 812, then a screenshot of the visible screen and one of the whole page.

    Streamlit scrolls inside its own panel, so the full-length picture is taken by making
    the window as tall as the content (same 375 px width) and then restoring it.
    """
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
    assert not overflow, f"{name}: page scrolls sideways at {PHONE['width']} px"
    peeking = page.evaluate("""() => { const bar = document.querySelector('[data-testid="stSidebar"]');
        if (bar.getAttribute('aria-expanded') !== 'false') return [];
        return [bar, ...bar.querySelectorAll('*')].filter(e => {
            const box = e.getBoundingClientRect();
            return getComputedStyle(e).visibility !== 'hidden' && box.width > 0 && box.height > 0
                   && box.right > 0 && box.left < window.innerWidth; }).map(e => e.tagName).slice(0, 5); }""")
    assert not peeking, f"{name}: the collapsed sidebar shows over the page"
    check_page(page, name, lang, results, folder)
    results[f"public_{name}"] = results.pop(name)
    height = page.evaluate("Math.max(...[...document.querySelectorAll('[data-testid=\"stMain\"], "
                           "[data-testid=\"stMainBlockContainer\"]')].map(e => e.scrollHeight))")
    page.set_viewport_size({"width": PHONE["width"], "height": min(int(height) + 120, 9000)})
    page.wait_for_timeout(700)
    page.screenshot(path=str(folder / f"{name}_full.png"))
    page.set_viewport_size(PHONE)
    page.wait_for_timeout(300)


def play_public_case(page, answer: str, shot: str | None, lang: str, results: dict, folder: Path) -> None:
    """Choose (the AI reveal is locked until then), reveal the AI, reveal the truth."""
    assert page.locator(".st-key-public_reveal_ai button").is_disabled(), "AI reveal not locked before choosing"
    tap(page, f"pick_{answer}")
    tap(page, "public_reveal_ai")
    page.locator(".booth-prediction").wait_for()
    if shot:
        check_phone(page, f"{shot}_ai", lang, results, folder)
    tap(page, "public_reveal_truth")
    page.locator(".booth-result").wait_for()
    if shot:
        check_phone(page, f"{shot}_truth", lang, results, folder)
    tap(page, "public_next")


def run_public_language(page, lang: str, results: dict, folder: Path) -> None:
    text = translations(lang)
    page.goto(PUBLIC_URL)
    page.locator('[data-testid="stSidebar"]').wait_for(state="attached")
    if lang == "ar":
        open_sidebar(page)
        page.locator('[data-testid="stSidebar"]').get_by_text(translations("ar")["language_name"],
                                                               exact=True).click()
        page.wait_for_timeout(1000)
        close_sidebar(page)
    page.get_by_text(text["public_home_intro"], exact=True).wait_for()
    check_phone(page, f"{lang}_home", lang, results, folder)

    # Challenge (a): a round of 5 random cases.
    phone_nav(page, text["public_challenge_title"])
    tap(page, "play_round")
    for index in range(5):
        play_public_case(page, "malignant", f"{lang}_challenge_round" if index == 0 else None,
                         lang, results, folder)
    page.locator(".booth-station").filter(has_text=text["station_message"]).wait_for()
    check_phone(page, f"{lang}_challenge_round_end", lang, results, folder)
    tap(page, "play_again")

    # Challenge (b): a card number, after a polite rejection of a wrong one.
    entry = page.locator(".st-key-card_number input")
    entry.fill("45")
    page.locator('[data-testid="stFormSubmitButton"] button').click()
    page.get_by_text(text["card_invalid"], exact=True).wait_for()
    entry.fill("17")
    page.locator('[data-testid="stFormSubmitButton"] button').click()
    page.get_by_text(text["round_progress"].format(current=1, total=1, card=17), exact=True).wait_for()
    zoom = page.locator("label.booth-zoom").first  # tap to enlarge, tap again to close
    zoom.click()
    assert zoom.evaluate("e => getComputedStyle(e).position") == "fixed", "image did not enlarge"
    zoom.click()
    play_public_case(page, "benign", f"{lang}_challenge_card17", lang, results, folder)
    tap(page, "play_again")
    page.locator(".st-key-show_wrong label").click()
    for cid in ("17", "folder6"):  # first and last of the six patient folders
        page.get_by_text(text[f"wrong_{cid}_text"], exact=True).wait_for()
    check_phone(page, f"{lang}_challenge_wrong_cases", lang, results, folder)

    # Tweak the Tumor: the microscope image follows the sliders.
    phone_nav(page, text["tweak_title"])
    picture = page.locator(".st-key-slide_view img")
    picture.wait_for()
    page.get_by_text(text["slide_caption"], exact=True).wait_for()  # the permanent caption
    before = picture.get_attribute("src")
    slider = page.locator('[data-testid="stSlider"] input[type="range"]').first  # nucleus size
    slider.focus()
    slider.press("End")  # largest nuclei
    page.get_by_text(text["slide_now"].format(name=text["nucleus_size"], look=text["nucleus_size_look"]),
                     exact=True).wait_for()
    page.wait_for_timeout(800)
    assert picture.get_attribute("src") != before, "the microscope image did not change with the slider"
    check_phone(page, f"{lang}_tweak", lang, results, folder)

    phone_nav(page, text["ask_title"])
    tap(page, "know_signs")
    box = page.locator('[data-testid="stChatInputTextArea"]')
    box.fill(text["know_signs"])
    box.press("Enter")
    page.get_by_text(text["chat_offline"], exact=True).first.wait_for()
    check_phone(page, f"{lang}_ask", lang, results, folder)

    phone_nav(page, text["about_title"])
    page.locator('[data-testid="stMetric"]').first.wait_for()
    check_phone(page, f"{lang}_about", lang, results, folder)


def snapshot(folder: Path) -> dict[str, tuple[int, int]]:
    return {path.relative_to(folder).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in folder.rglob("*") if path.is_file()
            and not {".git", "__pycache__"} & set(path.relative_to(folder).parts)}


def run_public(browser, python: str, results: dict) -> None:
    folder = OUTPUT / "public"
    folder.mkdir(parents=True, exist_ok=True)
    if not (PUBLIC_DIR / "public_app.py").is_file():
        raise RuntimeError("public_deploy/ is missing: run scripts/export_public.py first.")
    before = snapshot(PUBLIC_DIR)
    with (folder / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([python, "-c", PUBLIC_WRAPPER], cwd=PUBLIC_DIR, stdout=log,
                                  stderr=subprocess.STDOUT)
        try:
            wait_for_server(server, PUBLIC_URL)
            page = browser.new_page(viewport=PHONE, is_mobile=True, has_touch=True, device_scale_factor=2)
            page.on("pageerror", lambda error: results.setdefault("browser_errors", []).append(str(error)))
            page.set_default_timeout(30000)
            for lang in ("en", "ar"):
                run_public_language(page, lang, results, folder)
            page.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
    changed = sorted(set(before.items()) ^ set(snapshot(PUBLIC_DIR).items()))
    assert not changed, f"the public app wrote files: {changed}"
    results["public_files_written"] = 0
    results["public_python"] = python


def main() -> int:
    OUTPUT.mkdir(exist_ok=True)
    public_python = (sys.argv[sys.argv.index("--public-python") + 1] if "--public-python" in sys.argv
                     else sys.executable)
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
                run_public(browser, public_python, results)
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
