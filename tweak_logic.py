"""Tweak the Tumor: the rules shared by the Streamlit page and the web API. No Streamlit here."""
from __future__ import annotations

# WDBC feature name -> its translation key (the five booth labels and their *_help tooltips).
FRIENDLY_FEATURES = {"mean radius": "nucleus_size", "mean texture": "texture",
                     "mean smoothness": "smoothness", "mean concavity": "concavity",
                     "worst concave points": "concave_points"}
DEFAULT_THRESHOLD = 0.5


def decision(probability: float, threshold: float) -> tuple[str, float]:
    """(prediction, confidence shown in the gauge). At the threshold, the decision is malignant.

    Moving the threshold changes the decision, never the model's probability.
    """
    prediction = "malignant" if probability >= threshold else "benign"
    return prediction, probability if prediction == "malignant" else 1 - probability
