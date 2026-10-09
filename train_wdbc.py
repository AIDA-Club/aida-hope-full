"""Train the small Wisconsin (WDBC) model behind the "Tweak the Tumor" booth page.

Five cell-nucleus measurements -> StandardScaler -> LogisticRegression.
Run:  python train_wdbc.py
Saves: models/wdbc_model.pkl      (the fitted sklearn pipeline)
       models/wdbc_features.json  (name, min, max, median for each feature, for the sliders)
"""
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
FEATURES = ["mean radius", "mean texture", "mean smoothness", "mean concavity", "worst concave points"]
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

data = load_breast_cancer(as_frame=True)
X = data.frame[FEATURES].to_numpy()

# CAREFUL: in sklearn's version of this dataset 0 = malignant and 1 = benign
# (data.target_names == ['malignant', 'benign']). We turn the numbers into words,
# so the model's classes are literally "benign" / "malignant" and nobody can mix them up.
y = data.target_names[data.target]
assert (y == "malignant").sum() == 212 and (y == "benign").sum() == 357, "unexpected label mapping"

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=SEED)

model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED))
model.fit(X_train, y_train)

# ---- Evaluate on the held-out 20% ----
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
malignant_recall = recall_score(y_test, y_pred, pos_label="malignant")
cm = confusion_matrix(y_test, y_pred, labels=["benign", "malignant"])

print(f"Test samples: {len(y_test)} ({(y_test == 'malignant').sum()} malignant)")
print(f"Accuracy:         {accuracy:.3f}")
print(f"Malignant recall: {malignant_recall:.3f}  "
      f"(caught {cm[1, 1]} of {cm[1].sum()} malignant tumours, missed {cm[1, 0]})")
print("Confusion matrix (rows = truth, cols = prediction) [benign, malignant]:")
print(cm)

# Which way does each feature push? (positive = towards malignant, per standard deviation)
coefs = model[-1].coef_[0] * (1 if model.classes_[1] == "malignant" else -1)
print("\nEffect of +1 standard deviation (log-odds of malignant):")
for name, c in sorted(zip(FEATURES, coefs), key=lambda t: -abs(t[1])):
    print(f"  {name:22s} {c:+.2f}")

# ---- Save ----
with open(MODEL_DIR / "wdbc_model.pkl", "wb") as f:
    pickle.dump(model, f)

feature_info = [{"name": name,
                 "min": float(np.min(X[:, i])),
                 "max": float(np.max(X[:, i])),
                 "median": float(np.median(X[:, i]))}
                for i, name in enumerate(FEATURES)]
(MODEL_DIR / "wdbc_features.json").write_text(json.dumps(feature_info, indent=2))
print(f"\nSaved {MODEL_DIR / 'wdbc_model.pkl'} and {MODEL_DIR / 'wdbc_features.json'}")
