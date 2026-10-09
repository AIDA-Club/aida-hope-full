"""Optional real-browser verification. Requires playwright and local Chrome.

Starts its own headless server with a temporary results CSV. Never adds rounds
to the real booth CSV. Screenshots are saved in data/reports/verification/.
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/reports/verification"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wrapper = ("import sys; from pathlib import Path; import booth; booth.RESULTS_PATH=Path(sys.argv[1]); "
               "from streamlit.web import cli; sys.argv=['streamlit','run',sys.argv[2],"
               "'--server.headless','true','--server.address','127.0.0.1','--server.port','8502']; cli.main()")
    results = {}
    with tempfile.TemporaryDirectory() as temporary, (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, "-c", wrapper, str(Path(temporary) / "results.csv"),
                                   str(ROOT / "Home.py")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("The verification server exited before startup.")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8502/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("The verification server did not start.")
            results["headless_server"] = "started"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True,
                    executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
                page = browser.new_page(viewport={"width": 1920, "height": 1080})
                page.on("pageerror", lambda error: results.setdefault("browser_errors", []).append(str(error)))
                page.set_default_timeout(15000)
                page.goto("http://127.0.0.1:8502")
                page.get_by_role("link", name="Challenge the AI", exact=True).click()
                entry = page.locator('.st-key-case_number input')
                page.get_by_role("button", name="Show image", exact=True).wait_for()
                entry.fill("01")
                entry.press("Enter")
                try:
                    page.locator('.st-key-first_malignant button').wait_for()
                except Exception:
                    page.screenshot(path=str(OUTPUT / "failure.png"), full_page=True)
                    (OUTPUT / "failure.txt").write_text(page.url + "\n" + page.locator("body").inner_text(), encoding="utf-8")
                    raise
                page.get_by_role("heading", name="Challenge the AI", exact=True).click()
                for key, target in (("m", "reveal_ai"), ("r", "keep_answer"), ("k", "reveal_truth")):
                    page.wait_for_function("() => typeof window.__aidaBoothKeyHandler === 'function'")
                    page.keyboard.press(key)
                    page.locator(f'.st-key-{target} button').wait_for()
                    page.wait_for_function("selector => !document.querySelector(selector).disabled",
                                           arg=f'.st-key-{target} button')
                page.keyboard.press("t")
                page.locator('.booth-result').filter(has_text="You and the AI both got it right").wait_for()
                assert page.get_by_text("Did the AI look in the right place? Yes, mostly", exact=True).count() == 1
                assert page.locator('[data-testid="stImage"]').count() == 3
                assert page.locator('[data-testid="stException"]').count() == 0
                page.screenshot(path=str(OUTPUT / "challenge_case01.png"), full_page=True)
                results["case01"] = "rendered; Enter/M/R/K/T shortcuts passed; three images and overlap shown"
                results["case01_result_bounds"] = page.locator('.booth-result').bounding_box()
                page.keyboard.press("Escape")
                entry = page.locator('.st-key-case_number input')
                entry.wait_for(state="visible")
                for _ in range(50):
                    if entry.is_enabled():
                        break
                    page.wait_for_timeout(100)
                assert entry.input_value() == ""
                entry.fill("02")
                entry.press("Enter")
                page.locator('.st-key-first_normal button').wait_for()
                page.get_by_role("heading", name="Challenge the AI", exact=True).click()
                for key, target in (("n", "reveal_ai"), ("r", "change_answer"), ("c", "final_normal"), ("n", "reveal_truth")):
                    page.keyboard.press(key)
                    page.locator(f'.st-key-{target} button').wait_for()
                page.keyboard.press("t")
                page.locator('.booth-result').wait_for()
                assert page.get_by_text("Truth: Normal", exact=True).count() == 1
                assert page.get_by_text("Did the AI look in the right place?", exact=False).count() == 0
                assert page.locator('[data-testid="stException"]').count() == 0
                page.screenshot(path=str(OUTPUT / "challenge_normal.png"), full_page=True)
                results["normal_case02"] = "rendered; Esc/N/R/C/N/T shortcuts passed; null overlap hidden"
                page.keyboard.press("Escape")
                entry = page.locator('.st-key-case_number input')
                page.wait_for_function("() => !document.querySelector('.st-key-case_number input').disabled")
                entry.fill("17")
                entry.press("Enter")
                page.locator('.st-key-first_benign button').wait_for()
                page.get_by_role("heading", name="Challenge the AI", exact=True).click()
                for key, target in (("b", "reveal_ai"), ("r", "keep_answer"), ("k", "reveal_truth")):
                    page.keyboard.press(key)
                    page.locator(f'.st-key-{target} button').wait_for()
                    page.wait_for_function("selector => !document.querySelector(selector).disabled",
                                           arg=f'.st-key-{target} button')
                page.keyboard.press("t")
                page.locator('.booth-result').filter(has_text="Neither got it").wait_for()
                assert page.get_by_text("This is one of the cases our AI got wrong.", exact=True).count() == 1
                assert page.get_by_text("Did the AI look in the right place? No, it focused elsewhere", exact=True).count() == 1
                results["ai_error_case17"] = "B shortcut passed; pink error note and low-overlap result rendered"
                page.goto("http://127.0.0.1:8502/tweak")
                page.locator('.st-key-reset_benign button').click()
                page.locator('.booth-gauge-label').filter(has_text="Benign").wait_for()
                page.locator('.booth-gauge-number').filter(has_text="99%").wait_for()
                assert page.locator('.booth-gauge-number').inner_text() == "99%"
                page.wait_for_timeout(400)  # Let the class-bar width animation settle for the screenshot.
                page.screenshot(path=str(OUTPUT / "tweak_benign.png"), full_page=True)
                page.locator('.st-key-reset_malignant button').click()
                page.locator('.booth-gauge-label').filter(has_text="Malignant").wait_for()
                assert page.locator('.booth-gauge-number').inner_text() == "99%"
                assert page.get_by_text("Based on cell measurements from biopsy samples, not from the ultrasound images.", exact=True).count() == 1
                assert page.locator('[data-testid="stException"]').count() == 0
                page.wait_for_timeout(400)
                page.screenshot(path=str(OUTPUT / "tweak_malignant.png"), full_page=True)
                results["wdbc"] = "real model rendered; benign/malignant median resets each show 99%"
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            results["headless_server_stopped"] = server.poll() is not None
            (OUTPUT / "browser_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
