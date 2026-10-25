r"""Screenshots and end-to-end checks of the PinkAI website (frontend/) against the real API.

Needs both servers running (see README "Web redesign"):
    .venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
    npm --prefix frontend run dev            (port 5173)
Then:
    .venv\Scripts\python.exe scripts\redesign_screens.py [--base http://localhost:5173] [--only screens|flows]

Writes artifacts/screenshots/{desktop,tablet,mobile,arabic-desktop,arabic-mobile}/ and
artifacts/screenshots/flow_results.json. Exits 1 if any check fails.
Ask AIDA questions are answered by the API's own offline fallback when no API key is
configured; the script never needs a key and makes at most two chat requests.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "screenshots"
VIEWPORTS = {"desktop": (1536, 1024), "tablet": (768, 1024), "mobile": (390, 844)}
results: list[dict] = []


def design_pct(x: float) -> str:
    """The design's way of writing a probability: never "100%" or "0%" sure."""
    return ">99%" if x >= 0.995 else "<1%" if 0 < x < 0.005 else f"{round(x * 100)}%"


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""), flush=True)


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.evaluate("""() => Promise.all([...document.images].filter(i => !i.complete)
        .map(i => new Promise(r => { i.onload = i.onerror = r; })))""")
    page.wait_for_timeout(350)


def overflow(page: Page) -> int:
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def shoot(page: Page, folder: str, name: str) -> None:
    settle(page)
    path = OUT / folder / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)


def goto(page: Page, base: str, path: str, lang: str = "en") -> None:
    page.goto(f"{base}{path}{'&' if '?' in path else '?'}lang={lang}")
    page.wait_for_selector("main .screen")
    settle(page)


def leave_round(page: Page) -> None:
    if page.locator(".rail, .end-mascot").count():
        page.keyboard.press("Escape")
        page.wait_for_selector(".staff")


def beat_states(page: Page, base: str, folder: str, lang: str) -> None:
    """Waiting → card 17 → your call → the model's call → the truth → end, one screenshot each."""
    goto(page, base, "/beat", lang)
    leave_round(page)
    shoot(page, folder, "02-beat")
    page.locator(".staff input").fill("17")
    page.locator(".staff button[type=submit]").click()
    page.wait_for_selector(".choices")
    page.locator(".choice").nth(2).click()
    expect(page.locator(".choice[aria-checked=true]")).to_have_count(1)
    shoot(page, folder, "03-beat-your-call")
    page.locator(".stack-gap > .btn.wide").click()
    page.wait_for_selector(".probs-row")
    shoot(page, folder, "04-beat-model-call")
    page.locator(".stack-gap > .btn.wide").click()
    page.wait_for_selector(".three")
    shoot(page, folder, "05-beat-truth")
    page.locator(".next-row .btn").click()
    page.wait_for_selector(".end-mascot")
    shoot(page, folder, "06-beat-end")
    page.locator(".next-row .btn").click()
    page.wait_for_selector(".staff")


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
def flow_nav(page: Page, base: str) -> None:
    goto(page, base, "/")
    page.keyboard.press("Tab")
    check("a11y: first Tab reaches the skip link", page.evaluate("document.activeElement.className") == "skip-link")
    page.locator(".nav a", has_text="About").click()
    page.wait_for_selector("#about")
    check("nav: About link routes to /about", page.url.split("?")[0].endswith("/about"))
    check("nav: current page is marked", page.locator(".nav a[aria-current=page]").inner_text() == "About")
    page.locator(".lang button[lang=ar]").click()
    page.wait_for_function("document.documentElement.dir === 'rtl'")
    check("i18n: Arabic toggle sets dir=rtl and translates the nav",
          page.locator(".nav a[aria-current=page]").inner_text() == "عن المشروع")
    page.locator(".lang button[lang=en]").click()
    goto(page, base, "/beat?x=1")
    check("routing: a refresh on /beat serves the site", page.locator(".staff").count() == 1)


def flow_challenge(page: Page, base: str) -> None:
    api = page.request
    booth = {c["case_id"]: c for c in json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))}
    goto(page, base, "/beat")
    leave_round(page)
    page.locator(".staff input").fill("31")
    page.locator(".staff button[type=submit]").click()
    expect(page.locator("#case-hint")).to_contain_text("1 to 30")
    check("challenge: card 31 rejected with the existing card_invalid message", True)
    page.locator(".staff input").fill("#07")
    page.locator(".staff button[type=submit]").click()
    page.wait_for_selector(".choices")
    check("challenge: card '#07' starts card 7", page.locator(".rail .case").inner_text().strip() == "Card 7")
    state = api.get(f"{base}/api/challenge/round").json()["round"]
    check("challenge: no AI prediction or truth sent before the model's call",
          not {"ai_pred", "ai_probs", "truth", "heatmap", "overlay"} & set(state["case"]))
    check("challenge: heatmap refused before the model's call", api.get(f"{base}/api/challenge/image/heatmap").status == 404)
    check("challenge: reveal is locked until a call is made", page.locator(".stack-gap > .btn.wide").is_disabled())
    page.keyboard.press("m")  # keyboard shortcut: Malignant
    expect(page.locator(".choice[aria-checked=true]")).to_contain_text("Malignant")
    check("keys: M chooses Malignant", True)
    page.keyboard.press("r")  # keyboard shortcut: reveal the model
    page.wait_for_selector(".probs-row")
    case = booth["07"]
    shown = page.locator(".probs .pb b").all_inner_texts()
    expected = [design_pct(case["ai_probs"][k]) for k in ("normal", "benign", "malignant")]
    check("challenge: model probabilities equal data/booth_set.json", shown == expected, f"{shown} vs {expected}")
    check("challenge: model's call matches booth_set.json",
          case["ai_pred"].capitalize() in page.locator("h1").inner_text())
    check("challenge: AI-error note shown for a case the AI got wrong",
          page.locator(".error-note").count() == (0 if case["correct"] else 1))
    check("challenge: overlay refused before the truth", api.get(f"{base}/api/challenge/image/mask_overlay").status == 404)
    page.keyboard.press("t")  # keyboard shortcut: reveal the truth
    page.wait_for_selector(".three")
    truth_row = page.locator(".t-right .ledger .row").nth(3).inner_text()
    check("challenge: the truth matches booth_set.json", case["truth"].capitalize() in truth_row, truth_row)
    scores = [s.strip() for s in page.locator(".ledger.score .row b").all_inner_texts()]
    you = int(case["truth"] == "malignant")
    check("challenge: score counts the visitor and the model against the label",
          scores == [f"{you} of 1", f"{int(case['correct'])} of 1"], str(scores))
    page.locator(".next-row .btn").click()
    page.wait_for_selector(".end-mascot")
    check("challenge: one-card round ends with the station message",
          "AI helps doctors" in page.locator(".quote").inner_text())
    page.locator(".next-row .btn").click()
    page.wait_for_selector(".staff")

    page.locator(".staff .btn.ghost").click()
    page.wait_for_selector(".choices")
    cards, you_right, ai_right = [], 0, 0
    for index in range(5):
        count = page.locator(".rail .round-count").inner_text()
        check(f"challenge: random round shows case {index + 1} of 5", f"Case {index + 1} of 5" in count, count)
        card = "%02d" % int(re.search(r"(\d+)", page.locator(".rail .case").inner_text()).group(1))
        cards.append(card)
        page.locator(".choice").first.click()
        page.locator(".stack-gap > .btn.wide").click()
        page.wait_for_selector(".probs-row")
        page.locator(".stack-gap > .btn.wide").click()
        page.wait_for_selector(".three")
        you_right += booth[card]["truth"] == "normal"
        ai_right += booth[card]["correct"]
        page.locator(".next-row .btn").click()
        page.wait_for_selector(".choices, .end-mascot")
    check("challenge: five distinct cards in a random round", len(set(cards)) == 5, ",".join(cards))
    final = [s.strip() for s in page.locator(".ledger.score .row b").all_inner_texts()]
    check("challenge: final score equals the data", final == [f"{you_right} of 5", f"{ai_right} of 5"], str(final))
    page.locator(".next-row .btn").click()
    page.wait_for_selector(".staff")
    check("challenge: folders hidden by default", page.locator(".folder").count() == 0)
    page.locator(".switch").click()
    page.wait_for_selector(".folder")
    check("challenge: six patient folders shown on request", page.locator(".folder").count() == 6)


def flow_tweak(page: Page, base: str) -> None:
    goto(page, base, "/tweak")
    page.wait_for_selector("#call")
    page.locator(".presets .btn").nth(1).click()
    page.wait_for_timeout(700)
    check("tweak: typical malignant preset → Malignant", page.locator("#call").inner_text().lower() == "malignant")
    page.locator(".presets .btn").nth(0).click()
    page.wait_for_timeout(700)
    check("tweak: typical benign preset → Benign", page.locator("#call").inner_text().lower() == "benign")
    before = page.locator(".output .bars .b b").last.inner_text()
    page.locator(".threshold input").evaluate("""(el) => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        set.call(el, '0'); el.dispatchEvent(new Event('input', { bubbles: true })); }""")
    page.wait_for_timeout(700)
    after = page.locator(".output .bars .b b").last.inner_text()
    check("tweak: threshold changes the decision, not the probability",
          before == after and page.locator("#call").inner_text().lower() == "malignant", f"{before} / {after}")
    page.locator(".sliders input[type=range]").first.focus()
    for _ in range(40):
        page.keyboard.press("ArrowRight")
    page.wait_for_timeout(800)
    check("tweak: keyboard on a slider updates the microscope line", "Nucleus size" in page.locator(".microscope .now").inner_text())
    check("tweak: the microscope cell is drawn (canvas has nuclei over the slide)",
          page.locator(".cell-photo canvas").evaluate("""c => { const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
              let dark = 0; for (let i = 0; i < d.length; i += 4 * 97) if (d[i] < 90 && d[i + 2] > d[i + 1]) dark++; return dark > 50; }"""))


def flow_ask(page: Page, base: str) -> None:
    goto(page, base, "/ask")
    if page.locator(".new-chat").count():
        page.locator(".new-chat").click()
        page.wait_for_selector(".chips")
    page.locator(".topic-toggle").click()
    page.locator(".topic-menu .topic").first.click()
    page.wait_for_selector(".entry-topic")
    check("ask: topics menu closes after picking one", page.locator(".topic-menu .topics").count() == 0)
    check("ask: topic shows the hand-written Know the Signs answer", "Know the Signs" in page.locator(".entry-topic h3").inner_text())
    page.locator(".askbox .btn").click()
    expect(page.locator(".field-error")).to_have_text("Please type a question first.")
    check("ask: empty question refused with the existing chat_empty message", True)
    page.locator("#chat-input").fill("I found a lump, what should I do?")
    page.keyboard.press("Enter")
    page.wait_for_selector(".entry-assistant .aida-message")
    live = page.request.get(f"{base}/api/chat").json()["live"]
    reply = page.locator(".entry-assistant").last.inner_text()
    check("ask: typed symptom question answered (offline guidance when no key)", live or "see a doctor" in reply.lower(),
          "live" if live else "offline")
    check("ask: questions left counted", "11" in page.locator(".ask-form").inner_text())
    page.locator(".new-chat").click()
    page.wait_for_selector(".chips")
    check("ask: new conversation clears the transcript", page.locator(".entry").count() == 0)
    goto(page, base, "/ask?topic=get_help")
    page.wait_for_selector(".entry-topic")
    check("ask: ?topic=get_help opens Where to Get Help", "Where to Get Help" in page.locator(".entry-topic h3").last.inner_text())


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
                                                  reduced_motion="reduce")  # final states, not mid-animation
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    for name, path in (("01-home", "/"), ("07-tweak", "/tweak"), ("08-ask", "/ask"), ("09-about", "/about")):
                        goto(page, base, path, lang)
                        if path == "/tweak":
                            page.wait_for_selector("#call")
                        shoot(page, target, name)
                        px = overflow(page)
                        check(f"[{target}] {name}: no horizontal overflow", px <= 0, f"{px}px")
                    beat_states(page, base, target, lang)
                    check(f"[{target}] no console errors", not errors, "; ".join(errors[:3]))
                    context.close()
        if args.only != "screens":
            context = browser.new_context(viewport={"width": 1536, "height": 1024})
            page = context.new_page()
            flow_nav(page, base)
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
