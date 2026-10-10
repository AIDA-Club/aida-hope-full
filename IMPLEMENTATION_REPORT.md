# AIDA × Hope redesign — implementation report

- **Branch:** `redesign/claude` (local only; nothing pushed, merged or deployed)
- **Starting commit:** `5a09062` ("Heatmap-aware mistake lines; booth-set honesty note; heatmap caveat")
- **Brief:** `design/HOPE_REDESIGN_BRIEF.md`; ports from `design/RUN_CONFIG.md` (frontend 5173, backend 8000)
- **Run / test commands:** README → "Web redesign (React + FastAPI)"
- **Design decisions, reference → route map, tokens, artwork:** `DESIGN_MAP.md`

## Architecture

```
browser ── React + TypeScript (frontend/, Vite, react-router) ── /api/* ──▶ FastAPI (api/main.py)
                                                                           │
             booth.py · challenge_logic.py · tweak_logic.py · aida_chat.py · slide_image.py
                         (the same functions the Streamlit pages call)
```

- **No existing Python HTTP API existed**, so `api/main.py` is a thin FastAPI layer. It adds no
  model logic: predictions come from `booth.load_model_bundle()` + `booth.malignant_probability()`
  (same pickle, feature order, medians and threshold rule), cases from `booth.load_cases()`,
  chat answers from `aida_chat`, the microscope picture from `slide_image.render_jpeg()`.
- **Extracted, not rewritten:** the Challenge rules (`explanation_key`, `outcome_key`,
  `overlap_label`, `score`, folders) moved from `pages/1_Challenge_Reveal.py` into
  `challenge_logic.py`, and the Tweak feature labels and decision rule into `tweak_logic.py`.
  The Streamlit pages now import them, so both front ends share one implementation. The
  Streamlit apps (`Home.py`, `public_app.py`) are otherwise unchanged and still pass their
  tests; `scripts/export_public.py` copies the two new modules.
- **Session state and isolation:** each browser gets a random HttpOnly cookie; the server keeps
  that visitor's Challenge round and chat transcript in memory (`api/sessions.py`, 2 h idle
  expiry, capped). Like `public_app.py`, nothing visitor-related is written to disk (tested).
- **Spoiler-safe game:** the API sends the AI prediction/heatmap only after the visitor has
  answered and pressed Reveal AI, and the dataset label/overlay only after Reveal truth. The
  image endpoints refuse earlier requests (tested). A round snapshots its cases, as the booth does.
- **Translations:** the existing `i18n/en.json` / `ar.json` are served unchanged by
  `/api/i18n/{lang}`; strings that only the redesign needs are in
  `frontend/src/i18n/redesign.{en,ar}.json`. Python-style `{x:.0f}` formatting (with
  half-to-even rounding) is reproduced in `frontend/src/format.ts` (unit-tested).
- **Chat:** topic buttons return the hand-written `kb/fallback_*.md` sections; typed questions
  follow `pages/3_Ask_AIDA.py → answer()` exactly (live model when configured, otherwise the
  offline notice + safe fallback in the question's language, `fix_numbers` applied, 500-char and
  12-question limits). Replies are rendered by `aida_chat.message_html` (Markdown, raw HTML escaped).
  Settings: `.streamlit/secrets.toml` or `AIDA_PROVIDER`, `AIDA_API_KEY`, `AIDA_MODEL`,
  `AIDA_BASE_URL`, `AIDA_DAILY_CALL_CAP`.
- **Deployment shapes:** dev = Vite on 5173 proxying `/api` to uvicorn on 8000; production =
  `npm run build`, then the API also serves `frontend/dist` on port 8000 (SPA fallback).
- **Booth staff flow** (staff case entry, CSV results log, keyboard shortcuts) is not part of the
  redesign references and remains in the Streamlit booth app (`Home.py`). The redesign implements
  the public visitor flow (random round of five, or a printed card number).

## Tests actually run (final state)

| Check | Command | Result |
|---|---|---|
| Baseline before any change | `python -m pytest -q` | 91 passed |
| Python suite incl. new API tests | `python -m unittest discover -s tests` | **113 tests OK** (91 existing + 22 new in `tests/test_api.py`) |
| Prediction parity | `tests/test_api.py::TweakParityTests` | 45 deterministic inputs (medians, both presets, min, max, 40 seeded random rows): API probability **exactly equal** to `booth.malignant_probability`; threshold sweep incl. probability == threshold → malignant; microscope JPEG byte-identical to `slide_image.render_jpeg` |
| Challenge parity | `ChallengeTests` | all 30 cards: prediction, probabilities, label, AI-correct, explanation/outcome/overlap keys equal the original rules; page `explanation()` sentence equals the API key+values in EN and AR; phase gating; 5-case round scores once per reveal; card parsing incl. `#7`, `٧`; two clients isolated; results CSV untouched |
| Chat | `ChatTests` | topics = fallback sections (EN/AR); offline answers = page logic; empty / too long / 12-question limit / reset; live path with a stand-in `call_llm` (no network) incl. history and `fix_numbers`; failing live call falls back offline; env-var settings |
| Frontend typecheck | `npm --prefix frontend run typecheck` | OK (strict TS) |
| Frontend unit tests | `npm --prefix frontend test` | 4 passed (formatter) |
| Frontend build | `npm --prefix frontend run build` | OK (JS 228 kB / 73 kB gzip) |
| Browser flows + screenshots | `python scripts/redesign_screens.py` (dev servers) | **63/63 checks** (`artifacts/screenshots/flow_results.json`) |
| Same flows on the single-port build | `... --only flows --base http://localhost:8000` | 33/33 |
| Existing Streamlit smoke test | `python scripts/export_public.py && python scripts/smoke_test.py` | PASS (booth + exported public site, EN/AR, 0 files written) |
| API unreachable | stop uvicorn, open `/beat` | clear "server can't be reached" message + Try again (`desktop/99-error-api-offline.png`) |

Browser flows covered: skip link is the first Tab stop; nav routing; Arabic toggle sets
`dir=rtl` and translates; invalid card 31 rejected with the existing message; card `#07`
plays card 7; nothing leaked before reveal (JSON and image endpoints); AI percentages equal
`booth_set.json`; AI-error note; dataset label; scores; one-card and five-card rounds incl. end
screen; patient folders hidden until toggled, then six shown; Tweak presets give Malignant /
Benign; threshold to 0 flips the decision without changing the probability; keyboard arrows
on a slider update the microscope caption and image; Ask topic, empty-question error, offline
answer to a symptom question, question counter, New conversation. Every page at every
viewport (desktop 1536×1024, tablet 768×1024, mobile 390×844; EN and AR for desktop and
mobile) was checked for horizontal overflow (none) and console errors (none).

## Visual comparison and remaining differences

All eight reference states were rendered at 1536 × 1024 and inspected next to their reference
(`artifacts/screenshots/compare/*.jpg`); two correction passes fixed hero heights, title
scale, artwork sizing (alpha-noise trimming), card heights, stepper order, image letterboxing,
the mobile header and tablet card overflow. Remaining, known differences:

1. **Real data instead of mockup values.** Tweak starts at the feature medians, as the Streamlit
   page does (Nucleus size 13.37 → model 92% Benign); the mockup shows 10.54 / 99%. About and
   case #29 numbers match the mockups because they are the real results.
2. **Original copy kept where the mockup shortened it** (card text, "When the AI got it wrong"
   intro, confidence note, About limits) plus preserved notices the mockups omit: heatmap caveat
   under every heatmap, booth-set honesty note, chat disclaimer and offline/live note, question
   counter, image credits, and a "Leave this round" link. Beat intro, Tweak, About and the game
   states are therefore 40–120 px taller than 1024; the disclaimer footer sits just below the fold.
3. **Result headline:** the truth card uses the existing outcome lines ("The AI caught what you
   missed", etc.) and per-case explanation instead of the mockup's "The AI matched the label this
   time." (no such string in the repository).
4. **Images keep their true aspect ratio.** Ultrasounds and heatmaps are near-square and some
   include black scan borders, so the image frames are narrower than the mockups' landscape crops.
   The Home card stack shows real booth-card originals (darker than the mockup art); the About
   heatmap thumbnail is a real Grad-CAM (blue/red), not the mockup's pink blob.
5. **Typography:** Lexend/Outfit approximate the references' rounded geometric face; titles are
   slightly wider and the AIDA ray mark is a simplified SVG. Arabic uses Cairo.
6. **Artwork composition:** mascots/ribbons are separate reconstructed cutouts, so ribbon loops
   and mascot positions differ by a few tens of pixels from the flattened mockups; artwork is not
   pixel-exact (as the asset README states).
7. **Header:** unified (see DESIGN_MAP contradictions) — burgundy active pill on Home, no frame.
8. **Single-card rounds** show one progress dot ("Case 1 of 1 · Card #29"); the mockups depict a
   five-case round.

## Assumptions

- The redesign targets the public visitor experience; the staff booth flow stays in Streamlit.
- New UI strings were added only where the references show text the repository lacks; the
  Arabic versions are marked **DRAFT – needs native Arabic review**, like the existing `ar.json`.
- No project statistics or references were invented: every number comes from `metrics.json`,
  `booth_set.json` or the model; the About reference list is the existing `about_credits`.
- Python 3.12 venv was used (the public requirements were pinned on 3.12); the README's 3.11
  instructions still work for the Streamlit app.

## Files left untracked on purpose

`design/` (brief, references and supplied artwork, 198 MB, untracked when work started) is
not committed. The web-ready artwork derived from it is committed in `frontend/public/art/`;
`scripts/prepare_web_art.py` and the comparison step of `scripts/redesign_screens.py` read
`design/` when it is present.

## Not verified / blockers

- **Live Ask AIDA model:** no API key is configured on this machine, so the live provider call
  was not exercised end to end. The live code path is covered with a stand-in for
  `aida_chat.call_llm`; offline answers were verified in the browser. No remote chat calls were made.
- **Browsers:** automated checks ran in Playwright Chromium only (plus the in-app browser);
  Safari/Firefox were not tested (Firefox slider styles are included but unverified).
- **Screen readers:** semantics (landmarks, labels, radio group, switch, progressbars, live
  regions, skip link) were checked structurally, not with an actual screen reader.
- No other blockers.
