# AIDA × Hope

A bilingual Streamlit booth app for breast cancer awareness. Designed for Python
3.11 and a 27-inch display. Streamlit provides the UI; scikit-learn 1.6.1 is
included to deserialize the real WDBC pipeline. The demo generator uses Python's standard library.
No database, API key, external font, or internet connection is needed at runtime.

## Run on Windows

From this project folder, with Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run Home.py
```

Open http://localhost:8501. Use browser full-screen mode (F11) for the booth.
The language selector stays in the sidebar on every page. Arabic uses RTL
layout and locally installed Tahoma / Segoe UI fonts. Browser chrome and
Streamlit's built-in developer controls are provided by Streamlit; all application
labels are in `i18n/en.json` and `i18n/ar.json`. Knowledge-base copy is in the
two requested Markdown files.

On macOS/Linux, substitute `python3.11 -m venv .venv`, then use
`.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

## Active real data and preserved demo

`data/booth_set.json` now contains the **30 real exported cases**, numbered
`01`–`30`. Original images, heatmaps, reference overlays, and print images are
under `data/images/`, `data/heatmaps/`, `data/overlays/`, and `data/print/`.
The previous fake JSON is preserved as `data/booth_set_demo.json`, and fake
assets remain under `data/demo/`. The active app references only the real set.
Previous model files are preserved as `models/*_old.*`.

The app runs with the active real data immediately. To regenerate an offline
fake demo backup (never the active real JSON):

```powershell
.\.venv\Scripts\python.exe scripts/generate_demo.py
```

The generator refuses to replace the existing demo backup unless `--force` is
explicitly passed. `--force` replaces only `data/booth_set_demo.json` with FAKE data.
It only generates images under `data/demo/`; your existing raw data and
real image folders are preserved.

## Replace with real booth cases

1. Replace `data/booth_set.json` with a list of exactly 30 cases using the attached
   schema, with unique string IDs `01`–`30` and every required field.
2. Put the referenced local images under `data/`. All paths are relative to
   the `data` directory. For example, `images/case01.png` resolves to `data/images/case01.png`.
3. Supply original, print, heatmap, and mask-overlay images. For a normal case,
   its mask-overlay should not include a tumor outline.
4. Use class codes `normal`, `benign`, and `malignant`. Probabilities must each
   be within 0–1 and sum to 1 (tolerance 0.01). `correct` and `error_type` must
   agree with `truth` and `ai_pred`; overlap must be within 0–1 or `null` when no
   tumor overlap is available. Missing or invalid fields report their case ID
   and field name.
5. Use actual source filenames. Restart the app after replacing a dataset.

The loader checks all cases and image paths and displays a translated staff
error if the data is invalid. A running round keeps a snapshot of its case so
replacing the JSON cannot silently change its truth midway through that round.

## Challenge flow and logging

Staff enters a case number. The visitor chooses a first answer before seeing
the AI prediction. After revealing the AI and heatmap, they keep their answer
or select a new final answer. Only then can they reveal the truth and reference
overlay. The learning message compares the **final** visitor answer and the AI
prediction against truth.

Press Enter in the big case-number input to load a case. Staff shortcuts use
the same visible buttons: N/B/M choose an answer, R reveals the AI, K keeps the
answer, C changes it, T reveals truth, and Esc starts the next visitor. Shortcuts
follow the current phase and are disabled while typing. Esc can discard an
unfinished round; it cannot discard a completed round whose CSV save failed.
The original and heatmap appear side by side after AI reveal; the reference
overlay joins them after truth reveal. No scoreboard is displayed.

The overlap question appears only after truth reveal, for non-normal cases
with a numerical overlap: at least 0.3 is "Yes, mostly", 0.1 to below 0.3 is
"Partly", and below 0.1 is "No, it focused elsewhere". Normal and null-overlap
cases hide that question. An AI-error note is shown only after AI reveal.

Completing the truth reveal appends one row to `data/results.csv`:

```text
timestamp,case_id,first_answer,ai_pred,final_answer,truth
```

Timestamps are ISO 8601 in UTC; answers use stable English class codes in either
UI language. No name, contact details, free-text input, IP address, or visitor ID
is logged by the app. The CSV is created on the first completed round. Reruns,
navigation, and language changes do not append a second row for a saved round.
The next visitor can reuse the same case and will receive a new row.

A save failure leaves the completed round on screen for retry. Next visitor is
disabled until saving succeeds. Next visitor clears the case entry, answers,
and reveal state while retaining the language. One Streamlit server process
can serve multiple sessions; a process-local lock protects CSV writes. Do not
run multiple server processes writing the same CSV. Session state and append
logging are not a durable transaction across a server crash.

## Optional Tweak the Tumor model

Without both files, this page displays **Coming soon**. Add a trusted local
`models/wdbc_model.pkl` and `models/wdbc_features.json` when ready. Pickle files
can execute code: only use models supplied by your trusted team. There are no
model upload controls.

The model must implement `predict_proba([row])`, expose two `classes_`, and
accept a two-dimensional list of numerical measurements. If present,
`n_features_in_` and `feature_names_in_` must match the metadata count and order.
The requirements include scikit-learn 1.6.1, matching the exported model. Other
model formats need their own matching dependencies. A model that requires a DataFrame-only
interface needs an adapter accepting numerical rows.

Supported metadata: a list of feature objects, or an object with `features`
containing that list (or a mapping from feature names to their bounds).
Example; include at least five features in model input order:

```json
{
  "features": [
    {"name": "mean radius", "min": 5.0, "max": 30.0, "median": 14.0,
     "labels": {"en": "Mean radius", "ar": "متوسط نصف القطر"}},
    {"name": "mean texture", "min": 5.0, "max": 40.0, "median": 19.0},
    {"name": "mean perimeter", "min": 30.0, "max": 200.0, "median": 90.0},
    {"name": "mean area", "min": 100.0, "max": 2500.0, "median": 600.0},
    {"name": "mean smoothness", "min": 0.04, "max": 0.18, "median": 0.10}
  ],
  "class_labels": {"0": "malignant", "1": "benign"}
}
```

There are exactly five measurement sliders plus a decision-threshold slider.
The first five features vary; additional features remain at their medians.
The five booth labels and one-line tooltips are localized in `i18n/`: Nucleus
size, Texture, Smoothness, Concavity, and Concave points. Class strings `benign`
and `malignant` are supported. Default numerical mapping follows scikit-learn
WDBC: `0 = malignant`, `1 = benign`; set `class_labels` explicitly if your model
uses a different convention (for example `{"B": "benign", "M": "malignant"}`).
The adapter respects `classes_` order. At the threshold, the decision is malignant.
Moving the threshold changes the decision, not the underlying probability.

The large gauge shows the chosen class and that class's model probability.
The two class bars remain visible, including when a threshold changes the
chosen class. Lower thresholds trade more false alarms for fewer missed
cancers; higher thresholds trade fewer false alarms for more missed cancers.
These are biopsy cell measurements, not measurements from the ultrasound.

Reset buttons restore the per-class medians saved in `class_medians` and reset
the threshold to 0.5. If absent, `prepare_class_medians()` reconstructs the
local WDBC training split from `train_wdbc.py` (stratified, seed 42, 20% holdout).
It verifies the exported scaler's sample count and means before computing any
medians, then saves them with provenance in `models/wdbc_features.json`. No
refitting or external download occurs. The verified split contains 455 samples:
285 benign and 170 malignant. Back up metadata before swapping to another model.

All 68 original test images and their Grad-CAM views are saved under
`data/reports/gradcam_all/{originals,heatmaps,overlays}/`. The full activation
manifest is in `real_data_activation_report.md`.

## Ask AIDA

Four quick buttons load local sections from `kb/fallback_en.md` or
`kb/fallback_ar.md`. Preserve the stable `## know_signs`, `## myth_fact`,
`## explain_term`, and `## get_help` section identifiers when editing copy.
All answers work offline; source links can be opened when online. The clearly
marked `call_llm()` stub in `pages/3_Ask_AIDA.py` is not called by the current UI.
Add reviewed local service details to the help section before the booth event.

The fallback copy draws on the National Cancer Institute's
[symptoms](https://www.cancer.gov/types/breast/symptoms),
[screening](https://www.cancer.gov/types/breast/screening), and
[diagnosis](https://www.cancer.gov/types/breast/diagnosis) pages.
Navigation follows Streamlit's [multipage API](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation).

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite uses Streamlit's built-in AppTest and standard-library unittest.
It checks the bilingual flow, both answer paths, reveal ordering, reset,
CSV idempotency/retry, fake assets/schema, offline topics, and model integration.
Test CSVs and model fixtures live in temporary folders; no booth results are
created by tests.
