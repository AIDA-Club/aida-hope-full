# Patient folder selection (checked by eye, 9 Oct 2026)

Each candidate was opened in `gradcam_all/originals/`, `gradcam_all/heatmaps/`
and `gradcam_all/overlays/` and compared side by side. The overlay's pink line
is the reference tumor outline from the dataset mask.

**Result: all six planned cases tell their story. No swaps were needed.**

| # | Folder | Case | Truth → AI | Confidence | Overlap | Booth case |
|---|---|---|---|---|---|---|
| 1 | Confidently wrong | malignant_id_148 | malignant → benign | 91% benign | 0.03 | 17 |
| 2 | Missed cancer | malignant_id_143 | malignant → benign | 90% benign | 0.00 | 25 |
| 3 | Looked right, judged wrong | malignant_id_162 | malignant → benign | 56% benign | 0.81 | 26 |
| 4 | False alarm | benign_id_373 | benign → malignant | 77% malignant | 0.13 | 28 |
| 5 | Right answer, wrong reason | malignant_id_180 | malignant → malignant | 89% malignant | 0.06 | 04 |
| 6 | AI got it right (control) | malignant_id_153 | malignant → malignant | 99% malignant | 0.82 | not in booth set |

## What I saw

**1. malignant_id_148 (confidently wrong).** A small, dark, roundish mass sits
near the top-left of the image. The heatmap is a broad diagonal band running
from the upper left down to the lower right; its hottest areas are in the
middle and lower right of the image, in ordinary tissue. The warm edge of the
band only brushes the tumor. Story holds: 91% sure, and mostly looking
elsewhere. Burned-in label "LT AX" at the left edge; the heatmap is not on it.

**2. malignant_id_143 (missed cancer).** A dark, irregular mass in the upper
middle. The heatmap hot spot is a large block below and to the right of it;
the tumor outline is almost entirely in the cool (blue/cyan) zone. The clearest
"looked in the wrong place" example of the set. Burned-in label "LT10:00" at
the bottom; the heatmap does not sit on it.

**3. malignant_id_162 (looked right, judged wrong).** A large dark mass fills
much of the upper image. The heatmap's hottest region is squarely inside the
tumor outline. The model looked at the right place and still said benign (only
56%, a close call against 43% malignant). Good for "seeing isn't understanding".

**4. benign_id_373 (false alarm).** A dark oval lump with **caliper
measurement marks** (white "+" crosses, dotted lines and the numbers "1" and
"2") burned into the image. The hottest part of the heatmap is just right of
and below the lump, over the dark shadow beside it; the warm (yellow/orange)
area also covers the lower caliper cross and the "2" label. So the AI is partly
reacting to the area next to the lump and partly to the area with the
measurement marks. Worth mentioning to visitors: those marks were added by a
person who had already measured the lump, which is extra information the AI
should not be relying on. (We cannot prove the marks caused the prediction;
we can only say the heatmap overlaps them.)

**5. malignant_id_180 (right answer, wrong reason).** Two dark, rounded areas:
the outlined tumor on the right, and another large dark area on the left. The
heatmap is hottest on the left dark area and the tissue below it; the outlined
tumor is mostly in the cooler zone. Correct answer at 89% while looking mostly
outside the reference outline. Burned-in label "RTB AX" at the bottom left;
the heatmap is not on it.

**6. malignant_id_153 (control, AI got it right).** A dark, irregular,
shadowing mass in the middle of the image. The heatmap's hot spot sits inside
the upper part of the tumor outline. A small orientation icon is printed in
the bottom-right corner; the heatmap is not on it.

## Backups (reviewed, not used)

- **benign_id_416**: false alarm at 72%. Calipers are visible near the top
  around a small, flat lump; the heatmap ignores the lump and the calipers and
  lights up a deep region near the bottom of the image. A very strong "wrong
  place" example; use it if a second false-alarm folder is ever wanted.
- **normal_id_94**: healthy tissue called benign at 88%. Heatmap is a central
  vertical oval over ordinary tissue. No outline (normal case), so it is harder
  for visitors to judge.
- **benign_id_89**: false alarm at 65%. The real lump (a dark, smooth oval on
  the left) is ignored; the heatmap is on a different dark area on the right.
  Good, but folder 4 already covers false alarms.

## Notes for the owner

- Folders 1–5 use cases that are also in the 30-case booth challenge
  (booth cases 17, 25, 26, 28 and 04). A visitor who reads the folders first
  could learn those answers. Suggest showing the folders **after** the
  challenge, or keeping them at the staff side of the table.
- Folder 6 (malignant_id_153) is not one of the 30 booth cases; its images come
  from `gradcam_all/` only.
