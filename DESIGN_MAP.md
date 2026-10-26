# PinkAI website — design map

## Current design: PinkAI v2 (club board, "PinkAI site.zip", 25 Oct 2026)

The website uses the second version of the design a member of the club board delivered: the
"annotated notebook" (dotted paper, washi tape, Fraunces headings, Caveat handwriting, taped
photos, stamps, sticky notes, six mascot stickers) with v2's additions — nav icons and a phone
tab bar, the frosted "your case is waiting" deck, an AI-vs-you scoreboard, a "What radiologists
look for" clue card, the model's probabilities in the ledger, case-specific lessons and quotes,
a swipeable photo strip on phones, a live-drawn microscope cell with a sticky result strip on
narrow screens, and a full motion layer (drops, slams, pops, count-ups, draw-ons; all disabled
with "reduce motion"). It replaces v1 (`pinkai-site.zip`, 24 Oct), which replaced the earlier
"AIDA × Hope" look kept below for history.

**How it was implemented.** v2's stylesheet is used verbatim as the base of
`frontend/src/styles.css` (only the font family names changed, for the self-hosted fonts);
app-specific rules follow it. The pages were rebuilt in React to v2's markup and stay wired to
the FastAPI backend. v2 already used real data (`cases.js` exported from `booth_set.json`,
`wdbc.js` holding the trained model's coefficients); here the same data comes from the API, so
nothing is duplicated and the visitor's answers stay spoiler-safe (the prototype loads every
case's truth into the page).

| Design screen | Route | What drives it |
|---|---|---|
| Home | `/` | Card 17/4 originals; "21 of 24" etc. from `metrics.json` |
| Beat the AI · waiting | `/beat` (no round) | Card number or random card, plus a round of 5; AI-vs-you from `metrics.json`; clue card; six patient folders |
| Beat the AI · your call | `/beat`, `choose` | Any of the 30 cards; N/B/M keys |
| The model's call *(not in the prototype)* | `/beat`, `ai` | Real prediction, probabilities and heatmap; R/T keys |
| Beat the AI · the truth | `/beat`, `truth` | Real label, overlay, ticks, probabilities, case lesson and quote, score |
| End of round *(not in the prototype)* | `/beat`, `end` | Score, station message, AI-vs-doctors lessons |
| Tweak the Tumor | `/tweak` | Predictions from the API (the trained pipeline); the cell drawing is v2's canvas illustration (`frontend/src/pages/cell.ts`) over v2's `slide-bg.jpg` |
| Ask AIDA | `/ask` | Knowledge-base topics and the real chat (live when a key is set, offline otherwise) |
| About | `/about` | Every tile, bar and matrix cell from `metrics.json` |

**Decisions where v2 and the existing app differ**
- *Lessons and heat notes.* v2 writes its own case lessons with its own heatmap-overlap
  thresholds (40% / 15% / 0.5%), which differ from the tested Python rules
  (`challenge_logic.py`: 30% / 10%, 50% for "right on the lump"). To avoid two contradictory
  sentences on one screen, the hand-written note under the photos is the existing Python
  explanation, and v2's lesson wording is chosen from the API's own verdicts (`overlap_key`,
  `explanation_key`), not from new thresholds.
- *Probabilities* are written v2's way (never "100%" or "0%": ">99%", "<1%").
- *The dial* shows the chance of malignant, as in v2; the model's call is the line under it.
- *Step rail*: three steps (your call → the model's call → the truth); "keep or change" exists
  only in the staff booth app.
- *Waiting card*: the public site asks the visitor for their card number (v2: staff field),
  keeps v2's "or pick one at random", and adds "play a round of 5".
- *Clue card* ("What radiologists look for": shape, edges, direction, what is behind the lump)
  is the designer's content and is not in `kb/`; it carries his caveat "clues, not rules: only a
  biopsy can say for sure". Worth a check by the club's medical reviewer.
- *Microscope.* The Streamlit app's server-rendered picture (`/api/tweak/slide`) is no longer
  used by the website; v2's live canvas drawing is. Both are illustrations of the same real
  benign FNAC patch; the model never sees either. The original-image credits are unchanged.
- Kept from the earlier site: the "pink" in the headline is pink, full Arabic (v2 only flips
  direction; all new v2 text has draft Arabic), heatmap caveats, credits, the booth-card
  honesty note, the live chat, five-case rounds and patient folders.
- Fonts are self-hosted (no Google Fonts request; works offline). Arabic uses Cairo.

Artwork (`frontend/public/pinkai/`): the pink AIDA club logo, the six mascots (unchanged from
v1, converted to WebP) and `slide-bg.jpg` (v2's benign slide with the nuclei painted out).

---

# Earlier design (AIDA × Hope) — kept for history

Reference screenshots (`design/reference/`, 1536 × 1024) mapped to routes and states of the
React site (`frontend/`). Each implementation screenshot is in `artifacts/screenshots/desktop/`
and side by side with its reference in `artifacts/screenshots/compare/`.

| # | Reference file | Route / state | Component | Screenshot |
|---|---|---|---|---|
| 1 | `AIDA × Hope awareness activity hub-2.png` | `/` | `pages/Home.tsx` | `01-home.png` |
| 2 | `AIDA × Hope_ Beat the AI-1.png` | `/beat`, no round (intro) | `Beat.tsx` → `Intro`, `WrongCases` | `02-beat-intro.png` |
| 3 | `Beat the AI_ Make Your Choice-3.png` | `/beat`, round phase `choose` | `Beat.tsx` → `Play` + `Choose` | `03-beat-choice.png` |
| 4 | `Beat the AI with AIDA-4.png` | `/beat`, round phase `ai` | `Beat.tsx` → `AiReveal` | `04-beat-ai-reveal.png` |
| 5 | `AIDA heatmap truth reveal-5.png` | `/beat`, round phase `truth` | `Beat.tsx` → `Truth` | `05-beat-truth.png` |
| 6 | `Tweak the tumor measurement lab-7.png` | `/tweak` | `pages/Tweak.tsx` | `06-tweak.png` |
| 7 | `Ask AIDA at Hope Fair-6.png` | `/ask` | `pages/Ask.tsx` | `07-ask.png` |
| 8 | `AIDA × Hope_ Curiosity meets transparency-8.png` | `/about` | `pages/About.tsx` | `08-about.png` |
| – | (no reference) end of a round | `/beat`, round phase `end` | `Beat.tsx` → `End` | `05b-beat-end.png` |
| – | (no reference) API unreachable | any page | `ErrorBox` | `99-error-api-offline.png` |

The Beat the AI states are one route: the server keeps the round (per-visitor session) and
decides the phase, so a refresh resumes the same state and nothing about a case (AI answer,
heatmap, dataset label, overlay) reaches the browser before its phase. Screenshots 3–5 were
taken with card #29, the same card shown in references 4 and 5; its real values (Normal 86%,
Benign 13%, Malignant 1%, label Normal) match the mockups exactly.

## Token system (`frontend/src/styles.css`, `:root`)

One set of tokens was extracted from all eight references:

- **Ink**: `--ink #4a0924` (hero titles), `--ink-2 #5e0d30` (card headings), `--wine #8f1244`
  (active nav, eyebrow), `--muted #7b5d6e` (subtitles), `--soft #8a7480` (captions).
- **Brand**: `--rose #cf3772`, `--rose-deep #b5235c`, `--hot #ec3b78` ("Hope", checks,
  sparkles); primary buttons use the `--cta` gradient `#bd2a62 → #d6457d`.
- **Pastels** (panels, tiles, topic cards): pink `#fdedf2/#fbdbe6`, lilac `#f3effd/#e7defb`,
  peach `#fdf3ea/#fbe3d0`, blue `#ebf3fe/#d6e7fc` (blue ink `#1f4fb3` for "Your answer").
- **Surfaces**: page wash `#fcf0f4` with soft radial blushes; frosted white panels
  (`rgba(255,255,255,.66)`, 1.5px white border, `--shadow 0 18px 50px -20px rgba(176,45,96,.22)`).
- **Shape**: radii 30 / 24 / 18 / 12 px and full pills; 2px rounded-stroke line icons.
- **Type**: headings Lexend (variable, 720–820 weight, tight tracking); body Outfit; Arabic
  Cairo for both. All self-hosted through `@fontsource` (no internet needed at the booth).

## Contradictions between references, and how they were resolved

| Topic | What the references disagree on | Resolution |
|---|---|---|
| Active nav pill | Home shows bright pink; the other seven show deep burgundy | Burgundy (`#9c144b → #870f3f`) everywhere — the majority, and stronger contrast for white text |
| Header frame | Refs 4, 5, 7, 8 draw the header/page inside a rounded bordered frame; 1, 2, 3, 6 do not | No frame: one consistent unboxed header. The "07 · Ask AIDA" / "08 · About" labels above refs 7–8 are presentation captions, not UI |
| Title "03 · Make your choice" | Ref 3 prefixes the title with the deck slide number | Title is "Make your choice"; "03" is not product text |
| Round progress | Ref 3 uses a connected stepper beside the subtitle; refs 4–5 use loose dots under "Case 1 of 5" | One stepper (connected dots, ✓ for done cases) placed under the case label in all three states |
| "Your answer" icon | Pencil in ref 4, person in ref 5 | Kept as drawn: pencil after the AI reveal, person on the result |
| Primary button arrows | Circle-arrow on Home cards, plain arrow on game buttons, none on intro buttons | Kept per context, as drawn |
| Footer | Credits line on some pages only; "Behind the demo" link only on Home | Disclaimer on every page; image credits on game and Tweak pages; "Behind the demo" on Home |

## Artwork

`design/assets/` PNGs are copied by `scripts/prepare_web_art.py` into `frontend/public/art/`
as trimmed WebP. The supplied cutouts contained faint alpha noise (alpha ≤ 8) across the whole
canvas, which inflated their bounds (illustrations rendered at about half size) — that noise is
cleared before trimming; edges were inspected over dark and pink backgrounds with no halos.

| Where | Mascot | Ribbon |
|---|---|---|
| Home | `mascot-wave` | `ribbon-home` |
| Beat intro | `mascot-holding-card` | `ribbon-challenge` |
| Choose | `mascot-thinking` | `ribbon-choice` |
| AI reveal | `mascot-reveal-thinking`; `mascot-compare-mini` beside the speech bubble | `ribbon-reveal` |
| Truth / end | `mascot-result-happy-wave` | `ribbon-result` |
| Tweak | `mascot-tweak-thinking-wink` | `ribbon-tweak` |
| Ask | `mascot-ask-wave-wink`; `avatar-neutral` / `avatar-smiling` in chat; `mascot-curiosity` side panel | `ribbon-ask` |
| About | `mascot-about-wave`; `mascot-about-explore` in "A demo with clear limits" | `ribbon-about` |

Decorations (`sparkle-*`, `three-rays`, `rays-blue/purple`, `pink-petal`) and the Home/intro
illustrations (`measurement-sliders`, `bar-chart`, `chat-pink/lilac`, `question-disc`,
`fanned-cards`, `card-seven`, `neural-network`) are decorative and `aria-hidden`.

**Not used, on purpose:** `illustration-ultrasound-cards` (a reconstructed fake ultrasound) —
the Home card stack shows three real booth-card originals from the API instead; the raster
`icon-*` files — redrawn as one SVG icon set (`components/Icon.tsx`) so they stay sharp and
recolourable; `brand-aida-hope` raster wordmark — no original AIDA logo exists in the
repository, so the wordmark is live text plus an SVG ray mark (`Shell.tsx → Wordmark`).
The About thumbnails are a real test-set image and its real Grad-CAM heatmap (patient
folder 6, which is not a booth card, so it cannot spoil one).

## Brand update (PinkAI)

- The wordmark is now **PinkAI** ("Pink" in `--hot`, "AI" in `--ink`, with the ray mark), also in
  the page `<title>` and description. The Home headline is **"Think Pink, Ask AI"**, with "Pink"
  in `--hot` (`.title-pink`); the coloured word is a separate translation value
  (`home_headline_pink`), so the Arabic line colours its own word ("بالوردي", draft wording).
- An animated Home mascot (from a supplied video) was tried in `7ff38e6` and reverted at the
  owner's request; Home uses the static `mascot-wave` artwork again.

## Responsive and right-to-left

- ≤ 1180 px: Tweak becomes two columns plus a full-width output; About and Ask topics wrap.
- ≤ 980 px (tablet 768): nav collapses behind a menu button (Escape closes it); hero art
  shrinks beside the title; all two/three-column panels stack.
- ≤ 600 px (phone 390): hero art moves above the title; type scale steps down; footer lines hide.
- Arabic: `dir="rtl"` on `<html>`, logical CSS properties throughout, Cairo font, forward
  arrows / chevrons / send icon mirrored (`.icon-dir`), progress bars and slider fills grow
  from the right; numbers and the wordmark stay left-to-right.
