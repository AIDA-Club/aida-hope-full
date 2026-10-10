"""Screenshots and end-to-end checks of the React redesign (frontend/) against the real API.

Needs both servers running (see README "Web redesign"):
    .venv\\Scripts\\python.exe -m uvicorn api.main:app --port 8000
    npm --prefix frontend run dev            (port 5173)
Then:
    .venv\\Scripts\\python.exe scripts/redesign_screens.py [--base http://localhost:5173]

Writes artifacts/screenshots/{desktop,tablet,mobile,arabic,compare}/ and
artifacts/screenshots/flow_results.json. Exits 1 if any flow check fails.
Ask AIDA questions are answered by the API's own offline fallback when no API key is
configured; the script never needs a key and makes at most two chat requests.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "screenshots"
REFERENCE = ROOT / "design" / "reference"
REFERENCES = {
    "01-home": "AIDA × Hope awareness activity hub-2.png",
    "02-beat-intro": "AIDA × Hope_ Beat the AI-1.png",
    "03-beat-choice": "Beat the AI_ Make Your Choice-3.png",
    "04-beat-ai-reveal": "Beat the AI with AIDA-4.png",
    "05-beat-truth": "AIDA heatmap truth reveal-5.png",
    "06-tweak": "Tweak the tumor measurement lab-7.png",
    "07-ask": "Ask AIDA at Hope Fair-6.png",
    "08-about": "AIDA × Hope_ Curiosity meets transparency-8.png",
}
VIEWPORTS = {"desktop": (1536, 1024), "tablet": (768, 1024), "mobile": (390, 844)}
results: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""), flush=True)


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.evaluate("""() => Promise.all([...document.images].filter(i => !i.complete)
        .map(i => new Promise(r => { i.onload = i.onerror = r; })))""")
    page.wait_for_timeout(250)


def no_horizontal_overflow(page: Page) -> int:
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def shoot(page: Page, folder: str, name: str, full: bool = False) -> Path:
    settle(page)
    path = OUT / folder / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=full)
    return path


def compare(name: str, shot: Path) -> None:
    """Reference and implementation side by side at the same size."""
    ref = Image.open(REFERENCE / REFERENCES[name]).convert("RGB")
    ours = Image.open(shot).convert("RGB").resize(ref.size)
    sheet = Image.new("RGB", (ref.width * 2 + 24, ref.height + 40), "white")
    sheet.paste(ref, (0, 40))
    sheet.paste(ours, (ref.width + 24, 40))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 12), f"REFERENCE: {REFERENCES[name]}", fill="black")
    draw.text((ref.width + 34, 12), f"IMPLEMENTATION: {shot.name}", fill="black")
    target = OUT / "compare" / f"{name}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
def goto(page: Page, base: str, path: str, lang: str = "en") -> None:
    page.goto(f"{base}{path}?lang={lang}")
    page.wait_for_selector("main .page")
    settle(page)


def beat_states(page: Page, base: str, folder: str, lang: str = "en", card: str = "29") -> dict[str, Path]:
    """Intro → card → choose → AI → truth → end, screenshotting each state."""
    shots = {}
    goto(page, base, "/beat", lang)
    if page.locator(".play-panel, .end-panel").count():  # a round left over in this context
        page.locator(".quit-row button, .end-panel .cta").first.click()
        page.wait_for_selector(".beat-cards")
    shots["02-beat-intro"] = shoot(page, folder, "02-beat-intro")
    page.locator(".card-form input").fill(card)
    page.locator(".card-form button[type=submit]").click()
    page.wait_for_selector(".split-choose")
    check(f"[{folder}] reveal AI is locked until an answer is chosen",
          page.locator(".choice-side .cta-block").is_disabled())
    page.locator(".choice").nth(1).click()  # Benign
    expect(page.locator(".choice.is-selected")).to_have_count(1)
    shots["03-beat-choice"] = shoot(page, folder, "03-beat-choice")
    page.locator(".choice-side .cta-block").click()
    page.wait_for_selector(".split-reveal")
    shots["04-beat-ai-reveal"] = shoot(page, folder, "04-beat-ai-reveal")
    page.locator(".reveal-side .cta-block").click()
    page.wait_for_selector(".split-truth")
    shots["05-beat-truth"] = shoot(page, folder, "05-beat-truth")
    page.locator(".cta-next").click()
    page.wait_for_selector(".end-panel")
    shots["05b-beat-end"] = shoot(page, folder, "05b-beat-end")
    page.locator(".end-panel .cta").click()
    page.wait_for_selector(".beat-cards")
    return shots


def flow_challenge(page: Page, base: str) -> None:
    api = page.request
    booth = {case["case_id"]: case for case in json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))}
    goto(page, base, "/beat")
    # Card entry: invalid card is politely rejected, valid card plays exactly that case.
    page.locator(".card-form input").fill("31")
    page.locator(".card-form button[type=submit]").click()
    expect(page.locator(".field-error")).to_contain_text("1 to 30")
    check("challenge: card 31 rejected with the existing card_invalid message", True)
    page.locator(".card-form input").fill("#07")
    page.locator(".card-form button[type=submit]").click()
    page.wait_for_selector(".split-choose")
    check("challenge: card '#07' starts card 7", "Card #7" in page.locator(".case-label").inner_text())
    state = api.get(f"{base}/api/challenge/round").json()["round"]
    check("challenge: no AI prediction or truth sent before the AI reveal",
          not {"ai_pred", "ai_probs", "truth", "heatmap", "overlay"} & set(state["case"]))
    heat = api.get(f"{base}/api/challenge/image/heatmap")
    check("challenge: heatmap image refused before the AI reveal", heat.status == 404, str(heat.status))
    page.locator(".choice").nth(2).click()  # Malignant
    page.locator(".choice-side .cta-block").click()
    page.wait_for_selector(".split-reveal")
    case = booth["07"]
    bars = page.locator(".reveal-side .prob-label").all_inner_texts()
    expected = [f"{name} · {case['ai_probs'][name.lower()] * 100:.0f}%" for name in ("Normal", "Benign", "Malignant")]
    check("challenge: AI probabilities shown exactly as data/booth_set.json", bars == expected, f"{bars} vs {expected}")
    title = page.locator(".prediction-title").inner_text()
    check("challenge: AI prediction matches booth_set.json", case["ai_pred"].capitalize() in title, title)
    check("challenge: AI-error note shown for a case the AI got wrong",
          page.locator(".error-note").count() == (0 if case["correct"] else 1))
    truth = api.get(f"{base}/api/challenge/image/mask_overlay")
    check("challenge: truth overlay refused before the truth reveal", truth.status == 404, str(truth.status))
    page.locator(".reveal-side .cta-block").click()
    page.wait_for_selector(".split-truth")
    label = page.locator(".label-line").inner_text()
    check("challenge: dataset label matches booth_set.json", case["truth"].capitalize() in label, label)
    scores = page.locator(".score-value").all_inner_texts()
    you = 1 if case["truth"] == "malignant" else 0
    check("challenge: score counts the visitor and the AI against the label",
          [s.replace(" ", "") for s in scores] == [f"{you}/1", f"{int(case['correct'])}/1"], str(scores))
    page.locator(".cta-next").click()
    page.wait_for_selector(".end-panel")
    check("challenge: one-card round ends with the score and station message",
          "AI helps doctors" in page.locator(".station").inner_text())
    page.locator(".end-panel .cta").click()
    page.wait_for_selector(".beat-cards")

    # A random round of five: five distinct cards, scored once per truth reveal.
    page.locator(".play-card .cta-block").first.click()
    page.wait_for_selector(".split-choose")
    cards, you_right, ai_right = [], 0, 0
    for index in range(5):
        text = page.locator(".case-label").inner_text()
        check(f"challenge: random round shows case {index + 1} of 5", f"Case {index + 1} of 5" in text, text)
        card = "%02d" % int(re.search(r"#(\d+)", text).group(1))
        cards.append(card)
        page.locator(".choice").first.click()  # always "Normal"
        page.locator(".choice-side .cta-block").click()
        page.wait_for_selector(".split-reveal")
        page.locator(".reveal-side .cta-block").click()
        page.wait_for_selector(".split-truth")
        you_right += booth[card]["truth"] == "normal"
        ai_right += booth[card]["correct"]
        page.locator(".cta-next").click()
        page.wait_for_selector(".split-choose, .end-panel")
    check("challenge: five distinct cards in a random round", len(set(cards)) == 5, ",".join(cards))
    final = page.locator(".end-panel .score-value").all_inner_texts()
    check("challenge: final score equals the data", [s.replace(" ", "") for s in final] == [f"{you_right}/5", f"{ai_right}/5"],
          f"{final} expected {you_right}/5, {ai_right}/5")
    page.locator(".end-panel .cta").click()
    page.wait_for_selector(".beat-cards")

    # The six patient folders appear only when asked for.
    check("challenge: folders hidden by default", page.locator(".folder").count() == 0)
    page.locator(".switch").click()
    page.wait_for_selector(".folder")
    check("challenge: six patient folders shown on request", page.locator(".folder").count() == 6)


def flow_tweak(page: Page, base: str) -> None:
    goto(page, base, "/tweak")
    page.wait_for_selector(".gauge")
    page.locator("button.reset-button").nth(1).click()  # typical malignant
    page.wait_for_timeout(600)
    label = page.locator(".gauge-label").inner_text()
    check("tweak: typical malignant preset → model says Malignant", label == "Malignant", label)
    page.locator("button.reset-button").nth(0).click()
    page.wait_for_timeout(600)
    label = page.locator(".gauge-label").inner_text()
    check("tweak: typical benign preset → model says Benign", label == "Benign", label)
    before = page.locator(".lab-output .prob-label").first.inner_text()
    threshold = page.locator(".slider-threshold input")
    threshold.focus()
    threshold.evaluate("""(el) => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        set.call(el, '0'); el.dispatchEvent(new Event('input', { bubbles: true })); }""")
    page.wait_for_timeout(600)
    after = page.locator(".lab-output .prob-label").first.inner_text()
    check("tweak: threshold changes the decision, not the probability",
          before == after and page.locator(".gauge-label").inner_text() == "Malignant", f"{before} / {after}")
    size = page.locator(".lab-sliders input[type=range]").first
    size.focus()
    for _ in range(40):
        page.keyboard.press("ArrowRight")
    page.wait_for_timeout(700)
    check("tweak: keyboard on a slider updates the microscope caption",
          "Nucleus size" in page.locator(".lab-micro .lab-head p").inner_text())
    check("tweak: microscope image loads from the API",
          page.locator(".micro-frame img").evaluate("img => img.naturalWidth > 0"))


def flow_ask(page: Page, base: str) -> None:
    goto(page, base, "/ask")
    page.locator(".topic").first.click()
    page.wait_for_selector(".msg-topic")
    check("ask: topic button shows the hand-written Know the Signs answer",
          "Know the Signs" in page.locator(".msg-topic").inner_text())
    page.locator(".chat-form button[type=submit]").click()
    expect(page.locator(".field-error")).to_have_text("Please type a question first.")
    check("ask: empty question refused with the existing chat_empty message", True)
    page.locator("#chat-input").fill("I found a lump, what should I do?")
    page.keyboard.press("Enter")
    page.wait_for_selector(".msg-user >> nth=0")
    page.wait_for_selector(".msg-assistant .aida-message")
    live = page.request.get(f"{base}/api/chat").json()["live"]
    reply = page.locator(".msg-assistant").last.inner_text()
    check("ask: typed symptom question answered (offline guidance when no key)",
          live or "see a doctor" in reply.lower(), "live" if live else "offline")
    check("ask: turns left counted", "11" in page.locator(".chat-notes").inner_text())
    page.locator(".new-chat").click()
    page.wait_for_selector(".suggestions")
    check("ask: new conversation clears the transcript", page.locator(".msg-user").count() == 0)


def flow_nav_keyboard(page: Page, base: str) -> None:
    goto(page, base, "/")
    page.keyboard.press("Tab")
    check("a11y: first Tab reaches the skip link",
          page.evaluate("document.activeElement.className") == "skip-link")
    page.locator(".site-nav a", has_text="About").click()
    page.wait_for_selector(".page-about")
    check("nav: About link routes to /about", page.url.split("?")[0].endswith("/about"))
    page.locator(".lang-toggle button[lang=ar]").click()
    page.wait_for_function("document.documentElement.dir === 'rtl'")
    check("i18n: Arabic toggle sets dir=rtl and translates the nav",
          page.locator(".site-nav a.active").inner_text() == "عن المشروع")
    page.locator(".lang-toggle button[lang=en]").click()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5173")
    parser.add_argument("--only", choices=["screens", "flows"], default=None)
    args = parser.parse_args()
    base = args.base.rstrip("/")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        if args.only != "flows":
            for folder, size in VIEWPORTS.items():
                for lang in (("en", "ar") if folder != "tablet" else ("en",)):
                    target = folder if lang == "en" else f"arabic-{folder}"
                    context = browser.new_context(viewport={"width": size[0], "height": size[1]},
                                                  device_scale_factor=1)
                    page = context.new_page()
                    console = []
                    page.on("console", lambda m: m.type == "error" and console.append(m.text))
                    shots = {}
                    for name, path in (("01-home", "/"), ("06-tweak", "/tweak"), ("07-ask", "/ask"), ("08-about", "/about")):
                        goto(page, base, path, lang)
                        if path == "/tweak":
                            page.wait_for_selector(".gauge")
                        shots[name] = shoot(page, target, name)
                        shoot(page, target, f"{name}-full", full=True)
                        overflow = no_horizontal_overflow(page)
                        check(f"[{target}] {name}: no horizontal overflow", overflow <= 0, f"{overflow}px")
                    shots.update(beat_states(page, base, target, lang))
                    for name in ("02-beat-intro",):
                        goto(page, base, "/beat", lang)
                        shoot(page, target, f"{name}-full", full=True)
                    check(f"[{target}] no console errors", not console, "; ".join(console[:3]))
                    if target == "desktop":
                        for name, shot in shots.items():
                            if name in REFERENCES:
                                compare(name, shot)
                    context.close()
        if args.only != "screens":
            context = browser.new_context(viewport={"width": 1536, "height": 1024})
            page = context.new_page()
            flow_nav_keyboard(page, base)
            flow_challenge(page, base)
            flow_tweak(page, base)
            flow_ask(page, base)
            context.close()
        browser.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "flow_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
