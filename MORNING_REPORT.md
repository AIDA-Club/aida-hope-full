# Morning report: AIDA × Hope overnight work (Saturday)

Branch `overnight-saturday` (7 commits on top of the baseline). Nothing was
merged into `master`. **29 tests pass** (13 existing + 16 new), and a headless
browser smoke test passes on every page in English, Arabic and phone size.

## Done

| Task | What | Commit |
|---|---|---|
| 0 | `git init`, baseline commit on `master`, branch `overnight-saturday` | `df427b8` |
| 1 | All 9 candidate cases inspected by eye; final 6 folders confirmed, no swaps → `data/reports/folder_selection.md` | `bd2f707` |
| 2 | `print_content.yaml`: every printed word (folders, tips card, take-home card, poster, credits), EN + draft AR | `02e8ecb` |
| 3 | `scripts/build_print.py` → `print_out/` (case_cards, answer_key, folders, tips_card, takehome_cards, poster_A2) + 13 PNG previews, all checked by eye and fixed | `775ae1f` |
| 4 | `kb/` knowledge base (7 files + `system_prompt.md` + 2 fallbacks), live `call_llm()` with streaming and offline fallback (`aida_chat.py`, `pages/3_Ask_AIDA.py`), `.streamlit/secrets.example.toml`, `scripts/eval_chat.py`, `tests/chat_questions.yaml` (20 Qs), `tests/test_chat.py` | `2ae133e` |
| 5 | "What did we learn?" panel, About page, footer credits on every page, Arabic review flag, RTL list fix, `scripts/smoke_test.py`, `tests/test_polish.py` | `002a7a4` |
| 6 | Final rebuild of all PDFs and previews, README updated, all tests + smoke test re-run, this report | `343c62f` + report commit |

Final check results (last run):

- `unittest`: 29 tests OK.
- `scripts/smoke_test.py`: PASS. Home, Challenge (normal case 02 in English,
  AI-error case 17 in Arabic, both through to the closing panel), Tweak, Ask
  AIDA with no key, About; both languages, correct LTR/RTL, footer present, no
  exceptions; Ask AIDA at 390 px wide with no sideways scroll.
- The 30 case cards were scanned automatically: no class names, file names,
  percentages or verdict words on any card.
- Protected files (`data/booth_set.json`, images, heatmaps, overlays, print,
  `models/`, `data/results.csv`, existing `data/reports/` files, the notebook)
  are unchanged: `git diff master` shows only one added file there
  (`folder_selection.md`).

## Not done / problems

- **The live chatbot was never called for real.** There is no API key on this
  machine (correctly). The live path is tested with a fake client only, and
  `scripts/eval_chat.py` wrote a "Skipped: no keys" note to `tests/chat_eval.md`.
  Run it once you add a key (see below).
- **No `[NEEDS SOURCE]` markers were written into content**, because I only
  used the verified facts. But visitors will likely ask about these, and the
  knowledge base cannot answer them yet (the bot should say "I don't know, ask a
  doctor"):
  - "Does a bra / deodorant cause breast cancer?" (one of your eval questions)
  - UAE-specific screening programmes or ages (WHO's 50–69 is the only age range we have)
  - breastfeeding, self-examination guidance, and injury as a cause
- **Arabic diacritics are dropped in the printed PDFs** (see decisions). The app
  shows full diacritics; only the PDFs don't.
- **Folder images are soft when printed large.** The sources are 512 px; they
  are resampled to 300 dpi but cannot gain real detail. The 30 case cards use
  the existing 1748 px print images and look fine.
- **Take-home cards abut each other.** Each card's pink top strip sits right on
  the cut line, so a slightly off cut could leave a pink sliver on the card
  above. Ask the print shop to cut on the marks, or add a 3 mm gutter.
- I did not run the existing `scripts/verify_browser.py` (it would overwrite
  files in `data/reports/verification/`); `scripts/smoke_test.py` covers the
  same pages without touching anything.
- `i18n/ar.json` had no TODOs left to fill (all keys were already translated),
  so Task 5.3 became "add the review flag and translate the new keys".

## Decisions I made

- Git: the folder was not a repo. Ran `git init`; the default branch is
  `master` (not `main`). Baseline commit on `master`, all work on
  `overnight-saturday`.
- Git: added `Datasets/` (1.6 GB), `data_raw/`, `outputs/`, `export/`, `*.zip`
  and `models/*.pt` (2 × 45 MB) to `.gitignore` so the repo stays small. These
  files are untouched on disk; they are just not tracked.
- Git: the baseline commit was made with `user.name "ahmed"`; later commits use
  your global git identity (Ahmed Khalid).
- Task 1: kept all six planned folder cases; no swaps (see
  `data/reports/folder_selection.md`).
- Task 1: folders 1–5 reuse booth challenge cases 17, 25, 26, 28 and 04, so the
  folders reveal those answers. I did not change the booth set (it is
  protected); suggest showing folders after the challenge.
- Task 2: the folder cover does not show the folder's title (e.g. "Confidently
  wrong"), because it would give the verdict away; the title appears on the
  verdict page.
- Task 2: "Real result" lines say "Biopsy showed: ..." as part of the fictional
  story; the label actually comes from the dataset's ground truth.
- Task 2: removed one phrase I had drafted ("a lump that has not changed is
  reassuring") because it is not in the verified facts. Likewise in
  `kb/terms.md` I avoided describing a mammogram as an X-ray, and the real
  result caption says the outline is "from the dataset" rather than "drawn by
  experts".
- Task 2: the Arabic take-home card uses plural address (اعرفوا / راجعوا) so it
  speaks to women and men, since the card says men can get breast cancer too.
- Task 2: added two short labels for a simple drawing on the tips card
  (smooth wide oval vs irregular tall shape with a shadow). The drawing is a
  schematic, not a real scan; the wording repeats tips 3 and 4.
- Task 3 fonts: downloaded Amiri (Arabic) and Lato (Latin) from the official
  `google/fonts` GitHub repo into `assets/fonts/`, with their OFL licence files.
  The script falls back to Windows Arial / Segoe UI if they are missing.
- Task 3 Arabic: `arabic-reshaper` strips harakat (shadda, tanween) by default.
  I kept that, because reportlab cannot position combining marks reliably.
  Printed Arabic therefore has no diacritics (e.g. غالبا instead of غالباً).
- Task 3: every image is resampled (Lanczos) to exactly 300 dpi at its printed
  size and embedded as high-quality JPEG to keep the PDFs small (largest is
  case_cards.pdf at 10.7 MB).
- Task 3: confidences of 99.5% or more print as ">99%" and under 0.5% as "<1%",
  so nothing claims 100% or 0% certainty.
- Task 3 poster: the two example heatmaps are booth cases 01 (AI looked at the
  tumor) and 25 (AI looked elsewhere). Heatmaps only: no outline, case number
  or label, so the poster gives no answer away. The model line is shown with
  the "3 false alarms" and "68 images is a small test" notes.
- Task 3: the answer key labels wrong answers as "No: missed cancer" /
  "No: false alarm" and highlights those rows in pink.
- Task 3: case cards use an 8 mm margin (more than the 5 mm minimum) and add
  the line "Normal, benign or malignant? Decide before the AI does."
- Task 3: the take-home sheet's printer note sits in the top margin; cards are
  centred so the Arabic back lines up when printed double-sided (flip on long
  edge).
- Task 3: previews are rendered with `pypdfium2` (added to requirements).
- Task 4: the chat logic lives in a new module `aida_chat.py` (no Streamlit
  inside) so it can be unit-tested and reused by `scripts/eval_chat.py`. The
  page `pages/3_Ask_AIDA.py` only does the UI.
- Task 4: Gemini base URL `https://generativelanguage.googleapis.com/v1beta/openai/`
  was checked on Google's official OpenAI-compatibility page tonight. It can be
  overridden with `BASE_URL` in secrets. The example model names
  (`deepseek-chat`, `gemini-3.8-flash`) are only suggestions; check them when
  you add a key.
- Task 4: kept the existing National Cancer Institute "Learn more" links in the
  fallback answers. They were already there (not invented by me), and an
  existing test checks for them. The answer text itself now uses only the
  verified WHO facts.
- Task 4: when the assistant is offline, a typed question gets the closest
  hand-written answer, chosen by a simple keyword match (EN + AR keywords);
  "Where to Get Help" is the default when nothing matches. If the visitor types
  in Arabic, the Arabic fallback is shown even on the English screen.
- Task 4: the 20-second limit is applied twice: as the HTTP timeout and as a
  deadline for the whole streamed reply. Retries are off, so a visitor never
  waits much more than 20 seconds.
- Task 4: previous turns are sent to the model so follow-up questions work;
  they live only in the browser session (`st.session_state`), never on disk.
- Task 4: the bottom note now differs: offline it says nothing is sent
  anywhere; with a key it says typed questions go to an AI service.
- Task 4: added a "Men can't get breast cancer" myth to the Myth or Fact
  fallback, because the offline router sends "can men get breast cancer?"
  there.
- Task 4: `scripts/eval_chat.py` can compare several providers: besides the
  top-level PROVIDER/API_KEY/MODEL it reads optional `[deepseek]` and
  `[gemini]` sections (see `.streamlit/secrets.example.toml`). With no keys it
  writes a "Skipped" note to `tests/chat_eval.md`. Its phone/dose check also
  understands Arabic-Indic digits and Arabic dose units.
- Task 4: `about_booth.md` describes the model as ResNet18 starting from
  ImageNet weights, trained on Curated BUSI with a 314/68/68 split. I took
  these from `busi_pipeline.ipynb` and `metrics.json`.
- Task 5: added `"_review_status": "DRAFT - needs native Arabic review"` to
  `i18n/ar.json` and translated all the new keys. The translation-parity test
  now ignores keys that start with `_` (file metadata, not UI text).
- Task 5: the About page is in the sidebar navigation only; the home page keeps
  its three big cards (an existing test expects exactly three).
- Task 5: every number on the About page is read from
  `data/reports/metrics.json` at runtime, never typed in.
- Task 5: fixed an RTL bug that was already there: Arabic bullet lists had the
  dots on the far right and the text left-aligned. Lists now align right.
- Task 5: I wrote `scripts/smoke_test.py` (own server on port 8503, temporary
  results CSV, Ask AIDA forced offline, screenshots in `smoke_out/`, which is
  git-ignored) rather than running `scripts/verify_browser.py`.
- Task 5: the in-app browser pane could not take screenshots unattended, so all
  visual checks used headless Chrome via Playwright.
- Task 6: added `.claude/launch.json` (a dev-server config for the Claude app's
  preview pane). It is harmless; delete it if you don't want it.

## Needs the owner's review before printing

**Arabic (all drafts, need a native speaker):**

- [ ] `i18n/ar.json`: the whole file (`_review_status` flag added). New keys
      tonight: `chat_*`, `live_note`, `offline_note`, `learn_*`, `about_*`,
      `credits_short`.
- [ ] `kb/fallback_ar.md`: all four quick-button answers.
- [ ] `print_content.yaml`: every `ar:` block and `_ar` key (folder verdicts
      and safeguard lines; tips card; take-home card; poster;
      `credits.short_ar`; `meta.footer_ar`).
- [ ] Printed Arabic in `folders.pdf` (pages 5–6 of every folder),
      `tips_card.pdf` page 2, `takehome_cards.pdf` page 2, `poster_A2.pdf`.
- [ ] The 10 Arabic questions in `tests/chat_questions.yaml`.
- [ ] Wording choice: the take-home card uses plural address (اعرفوا / راجعوا).

**Placeholders (nothing real was invented):**

- [ ] `kb/help_uae.md`: `[TO VERIFY: Friends of Cancer Patients / Pink Caravan contact]`
- [ ] `kb/help_uae.md`: `[TO VERIFY: MoHAP]`
- [ ] `kb/help_uae.md`: `[TO VERIFY: Ajman services]`
- [ ] `kb/help_uae.md`: `[TO VERIFY: Sharjah services]`
- [ ] `print_content.yaml` → `takehome.qr_url`: `[TO VERIFY: Ask AIDA deployed URL]`.
      Until it changes, all 20 take-home cards print a **"PLACEHOLDER QR"** label
      and the QR code only encodes the placeholder text. Once a real URL is set,
      rebuild and the label disappears automatically.
- [ ] `[NEEDS SOURCE]`: none in content; see the missing topics under
      "Not done / problems".

**Folder wording (`print_content.yaml` → `folders`):**

- [ ] Fictional names (Mariam K., Fatima A., Noura S., Aisha R., Hessa M.,
      Layla H.), age ranges and scan reasons.
- [ ] "Biopsy showed: …" framing on the real-result pages.
- [ ] Folder 4 says the heatmap's warm area "also covers some of" the caliper
      marks. That is true of the heatmap, but we cannot prove the marks caused
      the prediction, so the wording stays careful.
- [ ] Consequence and safeguard bullets, and the six discussion questions.
- [ ] Decide when visitors see the folders (they reveal booth cases 04, 17, 25,
      26, 28).

**Other:**

- [ ] The QR URL (above).
- [ ] Poster (`print_out/poster_A2.pdf`): organisers line "AIDA Club × IEEE AU
      Student Cabinet · Hope Fair, Ajman University, 15 October 2026", the WHO
      theme line, and the credits.
- [ ] Answer key: keep it on the staff side.
- [ ] Print one test page of each PDF at 100% scale before the full run;
      check the take-home double-sided alignment.

## How to try it

All commands are PowerShell, run from the project folder:

```powershell
cd "C:\Users\ahmed\Desktop\AIDA x HOPE"
git checkout overnight-saturday
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the app (http://localhost:8501):

```powershell
.\.venv\Scripts\python.exe -m streamlit run Home.py
```

Rebuild all PDFs and previews (`print_out/` and `print_out/previews/`):

```powershell
.\.venv\Scripts\python.exe scripts\build_print.py
```

Run the tests, and the headless browser smoke test (screenshots in `smoke_out/`):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

Add an API key (the file is git-ignored; never paste the key anywhere else):

```powershell
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
notepad .streamlit\secrets.toml
```

Set `PROVIDER` (`deepseek` or `gemini`), `API_KEY` and `MODEL`, then restart
the app. To compare providers, also fill the optional `[deepseek]` / `[gemini]`
sections, then:

```powershell
.\.venv\Scripts\python.exe scripts\eval_chat.py
```

Read `tests/chat_eval.md`. Answers marked ⚠ contain digits that look like a
phone number or a dose, so read those first, but read the rest too.

## Suggested next steps for Sunday

1. Native Arabic review of everything in the checklist above.
2. Verify the four UAE contacts, write them into `kb/help_uae.md` and remove
   the `[TO VERIFY]` tags. Until then the bot is told never to share them.
3. Deploy Ask AIDA (e.g. Streamlit Community Cloud, with the key in its
   secrets settings), put the URL in `print_content.yaml` → `takehome.qr_url`,
   rebuild, and scan a printed QR with a phone.
4. Add a key and run `scripts/eval_chat.py`; fix the knowledge base or system
   prompt for any bad answers.
5. Decide whether to add verified sources for the common myths listed under
   "Not done" (bra, deodorant, UAE screening ages).
6. Test-print one page of each PDF (especially the A2 poster and the
   double-sided take-home sheet) before the full print run.
7. For booth day, consider hiding Streamlit's "Deploy" menu with
   `[client] toolbarMode = "viewer"` in `.streamlit/config.toml`.
8. Review the branch, then merge `overnight-saturday` into `master`.
