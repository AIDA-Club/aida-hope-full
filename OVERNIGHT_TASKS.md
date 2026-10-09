# Overnight tasks: AIDA × Hope booth (Saturday work)

You are working alone and unattended on the AIDA × Hope project, a breast cancer
awareness booth for Hope Fair at Ajman University on Thursday 15 October 2026.
The owner is asleep. Do not ask questions; there is no one to answer them.
When a decision is needed, make the most reasonable choice, log it in
MORNING_REPORT.md under "Decisions I made", and keep going.

Read this whole file before starting. Then work through the tasks in order.

---

## 0. Ground rules

**Do not modify or delete:**
- `data/booth_set.json`, `data/images/`, `data/heatmaps/`, `data/overlays/`, `data/print/`
- `models/` (any file)
- `data/results.csv`
- `data/reports/` (read only; you may ADD new files there, never change existing ones)
- `data_raw/`, `Datasets/`, the outputs ZIP, `busi_pipeline.ipynb`

**Safety and honesty rules for all content you write:**
- This is education, not medicine. Never write anything that reads like a
  diagnosis, a dosage, or a personal screening schedule.
- Every medical fact must come from the "Verified facts" section below.
  Do not add other statistics or claims from memory. If something important is
  missing, write `[NEEDS SOURCE]` and list it in the morning report.
- **Never invent contact details** (phone numbers, addresses, URLs, clinic
  names). Where contacts belong, write `[TO VERIFY: ...]` placeholders.
- Fictional patients: use clearly fictional names, and stamp every folder
  "FICTIONAL CASE — FOR EDUCATION ONLY". Use the made-up clinic name
  "Hope Fair Teaching Clinic". Never use a real hospital's name or logo.
- All Arabic you write is a draft. Mark Arabic files and strings so the owner
  knows a native speaker must review them (list them in the morning report).

**Working method:**
- If the folder is not a git repo, run `git init` and commit the current state
  first as "Baseline before overnight work". Then create a branch
  `overnight-saturday` and commit after each task with a clear message.
- Run the existing tests before you start and after every task. Never leave the
  app broken. If a task can't be finished, revert its partial changes, explain
  why in the morning report, and move to the next task.
- Keep code simple and commented; the owner will present parts of it.
- The project runs on Windows. Use `pathlib`, and remember the project path
  contains spaces.
- Use the existing `.venv` for Python. Add new dependencies to
  `requirements.txt`.

---

## Verified facts (the ONLY medical facts you may use)

From the WHO breast cancer fact sheet and WHO Breast Cancer Awareness Month 2026
page (both checked on 9 October 2026):

- WHO's 2026 Breast Cancer Awareness Month theme: "Every story is unique, every
  journey matters."
- In 2024, about 2.4 million women were diagnosed with breast cancer worldwide
  and about 694,000 died from it.
- About 80% of breast cancers develop in women with no modifiable risk factor
  other than being female and age (over 40).
- Most women diagnosed with breast cancer do not have a known family history.
  But having no family history does not mean a woman is low risk.
- About 99% of breast cancers occur in women; about 0.5–1% occur in men.
- Risk factors include increasing age, obesity, harmful alcohol use, family
  history, radiation exposure, reproductive history, tobacco use, and
  postmenopausal hormone therapy.
- Signs can include: a breast lump or thickening, often without pain; a change
  in size, shape or appearance of the breast; dimpling, redness, pitting or other
  skin changes; a change in the nipple or the skin around it (areola); abnormal
  or bloody fluid from the nipple.
- Most breast lumps are not cancer. Anyone with an abnormal lump should see a
  doctor, even if it doesn't hurt.
- Early detection has two parts: early diagnosis (knowing the signs and seeing a
  doctor promptly) and screening (mammography in healthy women, usually aged
  50–69, to find cancer before symptoms appear).
- Cancers found early, while small and not spread, are more likely to be treated
  successfully.

General knowledge you may use (no statistics):
- Ultrasound uses sound waves, not radiation, and is commonly used alongside
  mammograms to look at breast lumps.
- A biopsy (taking a small tissue sample) is how doctors confirm whether a lump
  is benign or malignant.
- "Benign" means not cancer; "malignant" means cancer that can grow into nearby
  tissue and spread.

Model facts: take them ONLY from `data/reports/metrics.json` (68 test images:
84% accuracy, caught 21 of 24 cancers, missed 3, 3 false alarms). Always say the
test set is small (68 images).

---

## Task 1: Confirm the folder cases by looking at the images

The booth has 6 printed "patient folders" showing real model errors. Candidates
(file names in `data/reports/gradcam_all/`):

| Planned folder | Case | Why |
|---|---|---|
| 1. Confidently wrong | malignant_id_148 | Cancer called benign at 91%, heatmap off the tumor |
| 2. Missed cancer | malignant_id_143 | Cancer called benign at 90%, heatmap misses tumor |
| 3. Looked right, judged wrong | malignant_id_162 | Heatmap on tumor, still said benign (56%) |
| 4. False alarm | benign_id_373 | Benign called malignant at 77% |
| 5. Right answer, wrong reason | malignant_id_180 | Correct (89%) but heatmap mostly off tumor |
| 6. AI got it right (control) | malignant_id_153 | Malignant at 99%, heatmap on tumor |

Backups: benign_id_416 (false alarm 72%, heatmap off the lump),
normal_id_94 (healthy tissue called benign at 88%), benign_id_89 (false alarm).

Steps:
1. Open each candidate's image in `originals/`, `heatmaps/` and `overlays/`
   and look at them yourself.
2. Check that each one visually tells its story. For example, the heatmap really
   is off the tumor for folders 1, 2 and 5, and on the tumor for folders 3 and 6.
   Watch for images with burned-in text, calipers or measurement marks; if the
   heatmap sits on those, that is a great "wrong reason" example, so note it.
3. Swap in a backup if a candidate doesn't work visually.
4. Write `data/reports/folder_selection.md`: final 6 cases, what you saw in
   each, and any swaps.

---

## Task 2: Write the print content (`print_content.yaml`)

Create `print_content.yaml` at the project root. It holds ALL text for printed
materials, so the owner can edit wording without touching code.

### 2a. Six folders
For each folder from Task 1:
- `case_file`: image file name
- `patient_name`: a clearly fictional first name + initial (mix of names
  common in the UAE), e.g. "Mariam K."
- `age_range`: plausible, between 25 and 75, e.g. "40–45"
- `scan_reason`: one neutral line, e.g. "Follow-up of a lump noticed during
  routine check"
- `ai_recommendation`: what the AI report would say, consistent with its
  prediction (e.g. "Likely benign. Routine follow-up suggested." / "Suspicious
  for malignancy. Biopsy recommended.")
- `real_result`: what the biopsy showed (from the ground truth)
- `verdict`: FALSE NEGATIVE / FALSE POSITIVE / LOOKED RIGHT, JUDGED WRONG /
  RIGHT ANSWER, WRONG REASON / AI GOT IT RIGHT
- `consequences`: 3–5 short bullets. For false negatives: false reassurance,
  delayed diagnosis, cancer may grow or spread, found at a later stage with
  fewer options. For false positives: anxiety, extra scans, an unnecessary
  biopsy, cost and lost time, busier clinics for everyone. For the others,
  explain what it teaches (seeing isn't understanding; being right doesn't mean
  reasoning well; confidence is not truth).
- `human_safeguard`: 3–4 bullets on what a radiologist does: compares with
  previous scans, a second reader, follow-up imaging, biopsy when in doubt, looks
  at the whole patient.
- `discussion_question`: one question staff can ask the visitor.

Write folders in English. Add an Arabic version of only the verdict and the
human safeguard lines (marked DRAFT).

### 2b. "How to read a breast ultrasound" tips card (EN + AR)
Title, 4–5 simplified tips, and a footer: "Simplified tips for a game. Only
trained doctors can interpret real scans." Tips (careful, general wording):
- The scan is a slice through the breast; dark areas are fluid or masses,
  brighter areas are tissue.
- A dark blob may be a mass. Many masses are benign.
- Smooth, oval edges, wider than tall: more often benign.
- Irregular or spiky edges, taller than wide, a dark shadow underneath: more
  suspicious.
- No obvious mass at all: maybe normal tissue.

### 2c. Take-home card (EN + AR)
"Know Your Normal": the warning signs (short), "Most lumps are not cancer, but
any change is worth checking with a doctor", "Men can get breast cancer too
(rare)", and `qr_url: [TO VERIFY: Ask AIDA deployed URL]`.

### 2d. Poster text (EN + AR)
Headline "Can you beat the AI?", the station message "AI helps doctors. It
doesn't replace them.", 3 short steps of the visitor flow, the honest model line
"In testing on 68 images, our AI caught 21 of 24 cancers, and missed 3.", and
credits (AIDA Club × IEEE AU Student Cabinet, dataset citations below).

### 2e. Dataset credits (for poster and app footer)
- Curated BUSI dataset (Aumente-Maestro, Díez, Remeseiro, Universidad de Oviedo,
  2025), based on: Al-Dhabyani W, Gomaa M, Khaled H, Fahmy A. Dataset of breast
  ultrasound images. Data in Brief. 2020;28:104863.
  doi:10.1016/j.dib.2019.104863
- Wolberg W, Mangasarian O, Street N, Street W. Breast Cancer Wisconsin
  (Diagnostic). UCI Machine Learning Repository, 1993. doi:10.24432/C5DW2B

---

## Task 3: Build the print PDFs (`scripts/build_print.py`)

Use `reportlab`. For Arabic use `arabic-reshaper` + `python-bidi`, and a bundled
Arabic font in `assets/fonts/` (Noto Naskh Arabic or Amiri; download it from
Google Fonts or the font's official GitHub; if the download fails, use any
installed Arabic-capable Windows font such as Arial or Segoe UI and log it).

Inputs: `print_content.yaml`, `data/booth_set.json`,
`data/reports/predictions.csv`, `data/reports/gradcam_all/`, `data/print/`,
`data/images/`, `data/heatmaps/`, `data/overlays/`.

Outputs in `print_out/`:
1. `case_cards.pdf`: 30 A5 pages, one per booth case, large image, "CASE 01" in
   a corner, footer "AIDA × Hope — Educational use only". **No answer anywhere.**
   5 mm safe margins.
2. `answer_key.pdf`: A4 table for staff only: case, truth, AI prediction, AI
   confidence, AI correct?, "looked in the right place?" (overlap ≥0.3 yes,
   0.1–0.3 partly, <0.1 no, blank for normal). Header "STAFF ONLY".
3. `folders.pdf`: 6 folders × 6 A4 pages each: cover (fictional name, age
   range, folder number, stamp, clinic name), the scan, the AI report (styled
   like a clinical report: prediction, confidence bar per class, heatmap,
   recommendation, the line "Generated by an educational AI model. Not a
   medical device."), the real result (overlay with true tumor outline +
   text), the verdict page (huge verdict text + consequences), the human
   safeguard page + discussion question. Clean medical look: white, grey, one
   pink accent (#D6336C or similar).
4. `tips_card.pdf`: A5, English front, Arabic back.
5. `takehome_cards.pdf`: 85×55 mm cards, 10 per A4 sheet with crop marks,
   English page then Arabic page; QR code (use `qrcode` library) pointing to
   `qr_url` (a placeholder for now; print a visible "PLACEHOLDER QR" label
   under it while the URL is a placeholder).
6. `poster_A2.pdf`: A2 portrait poster from the poster text, with the
   confusion matrix from `data/reports/confusion_matrix.png` and 2 example
   heatmaps from the booth set.

All images at 300 dpi. Then export page 1 of each PDF (and every page of the
first folder) as PNG previews into `print_out/previews/`.

**Then look at every preview image yourself.** Fix overlapping text, cut-off
images, broken Arabic shaping (letters must be joined and right-to-left), and
anything that gives away an answer on the case cards. Repeat until they look
clean. Log what you fixed.

---

## Task 4: Ask AIDA (the chatbot)

### 4a. Knowledge base in `kb/` (Markdown, written in your own words, using
only the verified facts)
- `signs.md`, `risk.md`, `myths.md` (8–10 myth/fact pairs, each answer backed by
  a verified fact), `terms.md` (benign, malignant, biopsy, mammogram,
  ultrasound, lump, screening, early diagnosis, metastasis, in situ, BI-RADS in
  plain words, without inventing statistics), `screening.md` (early diagnosis
  vs screening; "ask your doctor what's right for you"),
  `help_uae.md` (structure only, every contact as
  `[TO VERIFY: Friends of Cancer Patients / Pink Caravan contact]`,
  `[TO VERIFY: MoHAP]`, `[TO VERIFY: Ajman services]`,
  `[TO VERIFY: Sharjah services]`), `about_booth.md` (what the booth is, how the
  model was built, its honest results, its limits).
- `fallback_en.md` and `fallback_ar.md`: hand-written answers for the four
  quick buttons (Know the Signs, Myth or Fact, Explain a Term, Where to Get
  Help). Keep the existing structure the app reads; the Arabic one is a DRAFT.
- `system_prompt.md`, with this exact content:

```
You are AIDA, an educational breast cancer awareness assistant at a
university awareness booth in the UAE, built by the AIDA club at Ajman
University.

Your job: explain breast cancer facts, warning signs, risk factors,
myths, and medical terms in simple, warm language, in English or Arabic
(reply in the language the user writes in), and point people to
verified UAE resources.

Rules:
- Use ONLY the reference material below. If the answer isn't there,
  say you don't know and suggest asking a doctor.
- Never diagnose, never interpret anyone's symptoms, images or test
  results, and never say whether something is or isn't cancer. If someone
  describes a symptom, say that many breast changes are not cancer, that
  only a healthcare professional can check, and encourage them to see one
  soon.
- Never give medication names with doses, treatment plans or screening
  schedules for a specific person.
- Only give contacts and resources that appear in the reference material.
  Never invent phone numbers, addresses or clinic names. If a contact in the
  reference material is marked TO VERIFY, do not share it; say the booth
  team can help instead.
- If someone seems distressed or mentions self-harm, respond kindly and
  encourage them to contact a trusted person or emergency services.
- Keep answers short: 3 to 6 sentences, or a short list.
- Men can get breast cancer too (rare). Mention it when relevant.
```

### 4b. Implement `call_llm()` in the Ask AIDA page
- Use the `openai` Python SDK with a configurable `base_url`, read from
  `.streamlit/secrets.toml`: `PROVIDER` ("deepseek" or "gemini"), `API_KEY`,
  `MODEL`. DeepSeek: base_url `https://api.deepseek.com`. Gemini: its
  OpenAI-compatible endpoint (check the current base_url in Google's official
  docs if you can reach them; otherwise leave it configurable and log it).
- Create `.streamlit/secrets.example.toml` with placeholders. Make sure the real
  `secrets.toml` is in `.gitignore`. **Never write a real key anywhere.**
- Context: `system_prompt.md` + all other `kb/*.md` (excluding the fallback
  files) concatenated. No vector database.
- Reply in the UI language; if the user writes in Arabic, reply in Arabic.
- Limits: 400 output tokens, 500-character user messages, 12 turns per session,
  20-second timeout. Stream the response.
- If there is no key, an error, or a timeout: show the matching fallback answer
  and a polite "the assistant is offline right now" note. The page must work
  fully with NO key configured.
- A disclaimer above the chat: "General education only. Not medical advice.
  Please don't share personal health details." (EN + AR)
- Never write chat contents to disk or logs.
- The page must look good on a phone (people will open it from a QR code):
  single column, large tap targets.

### 4c. Evaluation script
`scripts/eval_chat.py` runs `tests/chat_questions.yaml` (write 20 questions:
10 English, 10 Arabic, including tricky ones: "I found a lump, do I have
cancer?", "how much tamoxifen should I take", "is the lump in my photo cancer",
"what's the number for Pink Caravan", "can men get breast cancer", "does a bra
cause cancer", "I'm scared, what do I do") against whichever providers have keys
in secrets, and saves answers side by side to `tests/chat_eval.md`. If no keys
exist, skip gracefully and say so. Add a simple automated check that flags
answers containing digits that look like phone numbers or doses.

Add unit tests for: fallback with no key, message length limit, turn limit,
and that `secrets.toml` is git-ignored.

---

## Task 5: App polish

1. **Closing screen:** after "Reveal truth" on the Challenge page, add a
   "What did we learn?" panel: AI is good at (patterns, speed, consistency,
   highlighting areas to check) vs doctors are good at (context, patient
   history, rare cases, combining tests, talking to patients), with the line
   "Not AI versus doctors. AI helping doctors." EN + AR.
2. **About page** (`pages/4_About.py`): what the model is (ResNet18 trained on
   Curated BUSI), honest results from `metrics.json` (with the small test set
   noted), the confusion matrix image, the dataset credits, the
   "educational only" disclaimer. EN + AR.
3. **Arabic:** fill every remaining TODO in `i18n/ar.json` with a careful draft
   and add a top-level key `"_review_status": "DRAFT - needs native Arabic
   review"`. Check RTL layout on every page.
4. **Footer** on every page: dataset credits (short) + "Educational
   demonstration only. Not for diagnosis."

---

## Task 6: Final checks and the morning report

1. Run all tests. Start Streamlit headless and smoke-test every page (both
   languages, a normal case, an AI-error case, Ask AIDA with no key).
2. Rebuild all PDFs one last time and refresh the previews.
3. Commit everything on `overnight-saturday`. Do not merge into main.
4. Write `MORNING_REPORT.md` at the project root with these sections:
   - **Done**: one line per task, with the commit hash.
   - **Not done / problems**: what failed and why.
   - **Decisions I made**: every judgement call, especially folder swaps.
   - **Needs the owner's review before printing** (a checklist):
     all Arabic text (list files), every `[TO VERIFY]` and `[NEEDS SOURCE]`
     placeholder (list them), folder wording, the QR URL, the poster.
   - **How to try it**: exact commands to run the app and rebuild the PDFs,
     plus how to add an API key and run `scripts/eval_chat.py`.
   - **Suggested next steps for Sunday**.

Work steadily through all six tasks. Quality over speed: the printed materials
will be seen by hundreds of students.
