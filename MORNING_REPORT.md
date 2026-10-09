# Morning report (work in progress)

## Done

- Task 1: folder cases checked by eye; `data/reports/folder_selection.md`.
- Task 2: `print_content.yaml` (all printed text, EN + draft AR).
- Task 3: `scripts/build_print.py` → 6 PDFs + previews in `print_out/`.

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

## Needs the owner's review before printing

## How to try it

## Suggested next steps for Sunday
