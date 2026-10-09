# Morning report (work in progress)

## Done

- Task 1: folder cases checked by eye; `data/reports/folder_selection.md`.
- Task 2: `print_content.yaml` (all printed text, EN + draft AR).
- Task 3: `scripts/build_print.py` → 6 PDFs + previews in `print_out/`.
- Task 4: knowledge base in `kb/`, live `call_llm()` (in `aida_chat.py`, used by
  `pages/3_Ask_AIDA.py`), `scripts/eval_chat.py`, `tests/chat_questions.yaml`,
  `tests/test_chat.py` (13 new tests).
- Task 5: "What did we learn?" panel, About page, footer credits, Arabic review
  flag, RTL list fix, `tests/test_polish.py` (3 new tests),
  `scripts/smoke_test.py` (headless browser check of every page, EN + AR + phone).

## Not done / problems

## Decisions I made

- Git: the folder was not a repo. Ran `git init`; the default branch is
  `master` (not `main`). Baseline commit on `master`, all work on
  `overnight-saturday`.
- Git: added `Datasets/` (1.6 GB), `data_raw/`, `outputs/`, `export/`, `*.zip`
  and `models/*.pt` (2 × 45 MB) to `.gitignore` so the repo stays small. These
  files are untouched on disk; they are just not tracked.
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
  reassuring") because it is not in the verified facts.
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
- Task 3: source images are 512 × 512 px. Every image is resampled (Lanczos) to
  exactly 300 dpi at its printed size, but detail is still limited by the
  source; the booth case cards use the pipeline's existing 1748 px print images.
- Task 3: confidences of 99.5% or more print as ">99%" and under 0.5% as "<1%",
  so nothing claims 100% or 0% certainty.
- Task 3 poster: the two example heatmaps are booth cases 01 (AI looked at the
  tumor) and 25 (AI looked elsewhere). Heatmaps only: no outline, case number
  or label, so the poster gives no answer away.
- Task 3: the answer key labels wrong answers as "No: missed cancer" /
  "No: false alarm" and highlights those rows in pink.
- Task 3: the take-home sheet's printer note sits in the top margin; cards are
  centred so the Arabic back lines up when printed double-sided (flip on long
  edge).
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
  "Where to Get Help" is the default when nothing matches.
- Task 4: the 20-second limit is applied twice: as the HTTP timeout and as a
  deadline for the whole streamed reply. Retries are off, so a visitor never
  waits more than about 20 seconds.
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
  writes a "Skipped" note to `tests/chat_eval.md`.
- Task 4: `about_booth.md` describes the model as ResNet18 starting from
  ImageNet weights, 224 px, trained on Curated BUSI with a 314/68/68 split. I
  took these from `busi_pipeline.ipynb` and `metrics.json`.
- Task 5: `i18n/ar.json` had **no** remaining TODOs; every key was already
  translated. I added `"_review_status": "DRAFT - needs native Arabic review"`
  and translated all the new keys. The translation-parity test now ignores
  keys that start with `_` (file metadata, not UI text).
- Task 5: the About page is in the sidebar navigation only; the home page keeps
  its three big cards (an existing test expects exactly three).
- Task 5: every number on the About page is read from
  `data/reports/metrics.json` at runtime, never typed in.
- Task 5: fixed an RTL bug that was already there: Arabic bullet lists had the
  dots on the far right and the text left-aligned. Lists now align right.
- Task 5: I did not run the existing `scripts/verify_browser.py`, because it
  overwrites files in `data/reports/verification/` (read-only for me tonight).
  I wrote `scripts/smoke_test.py` instead: own server on port 8503, temporary
  results CSV, Ask AIDA forced offline, screenshots in `smoke_out/`
  (git-ignored).
- Task 5: the in-app browser pane could not take screenshots unattended, so all
  visual checks used headless Chrome via Playwright.

## Needs the owner's review before printing

## How to try it

## Suggested next steps for Sunday
