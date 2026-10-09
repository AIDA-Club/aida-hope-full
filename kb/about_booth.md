# About the AIDA × Hope booth

## What the booth is

AIDA × Hope is a breast cancer awareness booth at Hope Fair, Ajman University,
on 15 October 2026. It was built by the AIDA club at Ajman University with the
IEEE AU Student Cabinet. It is for education only. It does not diagnose anyone.

Visitors can:

1. **Challenge the AI**: look at a real, anonymous breast ultrasound image,
   choose normal, benign or malignant, then see what the AI predicted, where it
   looked (a heatmap), and the true answer.
2. **Tweak the Tumor**: move cell measurements from a different public dataset
   and watch a simple model change its prediction.
3. **Ask AIDA**: ask this assistant general questions about breast cancer.

## How the image model was built

- It is a ResNet18, a common image-recognition network, that started from a
  model pre-trained on everyday photos and was then trained on breast
  ultrasound images.
- Training data: the Curated BUSI dataset (Universidad de Oviedo, 2025), based
  on the BUSI breast ultrasound dataset by Al-Dhabyani and colleagues (2020).
  Each image is labelled normal, benign or malignant.
- The images were split into 314 for training, 68 for checking during
  training, and 68 for the final test.
- The heatmaps are made with a method called Grad-CAM. They show which parts
  of the image most influenced the prediction. A heatmap shows where the AI
  looked, not whether it understood what it saw.

## Honest results (68 test images)

- Overall, it was right on about 84% of the 68 test images.
- Of 24 cancers (malignant), it caught 21 and missed 3.
- It raised 3 false alarms: benign lumps that it called malignant.
- 68 images is a small test, so these numbers could be quite different on
  other images.

## Limits

- It is an educational model, not a medical device. It must never be used to
  make decisions about anyone's health.
- It learned from one public dataset, so it may do worse on images from other
  machines, hospitals or people.
- It only sees one image. A doctor looks at the whole patient: their history,
  previous scans, other tests and, when in doubt, a biopsy.
- It can be confidently wrong, and it can be right for the wrong reason.
- AI helps doctors. It doesn't replace them.

## Datasets

- Curated BUSI dataset (Aumente-Maestro, Díez, Remeseiro, Universidad de
  Oviedo, 2025), based on: Al-Dhabyani W, Gomaa M, Khaled H, Fahmy A. Dataset
  of breast ultrasound images. Data in Brief. 2020;28:104863.
- Wolberg W, Mangasarian O, Street N, Street W. Breast Cancer Wisconsin
  (Diagnostic). UCI Machine Learning Repository, 1993. (Used by Tweak the
  Tumor.)
