# About the AIDA booth

## What this booth is
- **AIDA** is a bilingual (English/Arabic) breast cancer awareness chatbot.
- It was built by **AIDA Club × IEEE AU Student Cabinet** for the **Hope Fair at Ajman University, 15 October 2026**.
- **AIDA is for education only. It is not a medical device.** It cannot diagnose anyone, and it does not replace a doctor.

## The ultrasound AI demo
**How it was built**
- The model is **ResNet18**, an image-recognition network first trained on ImageNet (a large collection of everyday photos).
- It was then fine-tuned (re-trained) on breast ultrasound images from the **Curated BUSI dataset** (Universidad de Oviedo, 2025).
- Curated BUSI is based on the BUSI breast ultrasound dataset by Al-Dhabyani et al. (2020).
- The images were split into **314 for training, 68 for validation (tuning) and 68 for the final test**.

**Results on the 68 test images**
- **Accuracy: 84%** (about 57 of the 68 images classified correctly).
- 24 test images showed cancer:
  - The model **caught 21 of 24 cancers** (sensitivity 87.5%).
  - It **missed 3 cancers** (false negatives).
- It gave **3 false alarms**: benign (not cancer) images labelled as malignant (false positives).
- The model sorts each image into three groups: normal, benign or malignant. The other **5 errors** were mix-ups between normal and benign. Neither is cancer, so these did not change whether a cancer was caught (3 + 3 + 5 = 11 errors; 57 of 68 correct).
- ROC-AUC for spotting cancer was 0.955 (1.0 would be perfect).

**Treat these numbers with care**
- 68 test images is a **small test set**. A few images more or less right would change the percentages noticeably.
- All images came from one public research dataset. The model may perform differently on other machines, hospitals or people.
- Missing 3 of 24 cancers shows why an AI tool must never be used alone.
- Doctors use much more than one image: history, examination, other imaging and, when needed, a biopsy, which is the only way to confirm cancer.

## Heatmaps (Grad-CAM)
- The coloured heatmap (made with a method called Grad-CAM) shows **which parts of the image most influenced the model's answer**, that is, where it "looked."
- A heatmap is **not a diagnosis**. A bright area does not mean cancer is there, and the model can focus on the wrong area.
- If a score is shown, it tells how strongly the model leans toward an answer. **It is not the chance that a person has cancer.**

## Tweak the Tumor
- This interactive demo uses the **Breast Cancer Wisconsin (Diagnostic) dataset**, which contains **cell measurements from biopsy samples**.
- It shows how measurements of cells relate to a model's benign or malignant prediction. It is a learning game, not a test of anyone's health.

## AI helps doctors; it does not replace them
- In medicine, computer-aided detection software marks suspicious areas, and the **radiologist makes the final reading** (NCI).
- WHO says AI can help make diagnosis faster and more accurate, but people should stay in control of medical decisions.
- If you notice a change, see a doctor. Ajman University students and staff can visit the University Health Clinic. In an emergency, call **998**.

## Sources
- AIDA project documentation (booth team): model, dataset split and test results.
- Curated BUSI breast ultrasound dataset, Universidad de Oviedo (2025).
- Al-Dhabyani W, Gomaa M, Khaled H, Fahmy A. Dataset of breast ultrasound images. Data in Brief, 2020: https://doi.org/10.1016/j.dib.2019.104863
- Breast Cancer Wisconsin (Diagnostic) dataset, UCI Machine Learning Repository: https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic
- NCI Dictionary, computer-aided detection system: https://webapis.cancer.gov/glossary/v1/Terms/search/Cancer.gov/Patient/en/computer?matchType=Begins&size=20
- WHO Arabic, First global report on AI in health and six guiding principles (2021): https://www.who.int/ar/news/item/18-11-1442-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use
- NCI Dictionary, biopsy: https://webapis.cancer.gov/glossary/v1/Terms/search/Cancer.gov/Patient/en/biopsy?matchType=Contains&size=100
