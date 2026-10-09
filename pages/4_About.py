"""About: what the model is, its honest results, its limits and the dataset credits."""
import json

import streamlit as st

from booth import ROOT, t

REPORTS = ROOT / "data" / "reports"


def load_metrics() -> dict | None:
    """All numbers on this page come from data/reports/metrics.json (never typed in by hand)."""
    try:
        return json.loads((REPORTS / "metrics.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


st.title(t("about_title"))
st.write(t("about_intro"))
metrics = load_metrics()

st.header(t("about_model_heading"))
if metrics:
    sizes = metrics["split_sizes"]
    st.write(t("about_model_text", train=sizes["train"], val=sizes["val"], test=sizes["test"]))

st.header(t("about_results_heading"))
if metrics is None:
    st.error(t("about_metrics_missing"))
else:
    n = metrics["n_test"]
    caught, missed = metrics["malignant_caught"], metrics["malignant_missed"]
    cards = ((t("about_metric_images"), str(n)),
             (t("about_metric_accuracy"), f"{metrics['accuracy'] * 100:.0f}%"),
             (t("about_metric_caught"), t("about_caught_value", caught=caught, total=caught + missed)),
             (t("about_metric_alarms"), str(metrics["false_alarms"])))
    for column, (label, value) in zip(st.columns(4), cards):
        column.metric(label, value, border=True)
    st.write(t("about_results_text", n=n, accuracy=metrics["accuracy"] * 100, caught=caught,
               total=caught + missed, missed=missed, alarms=metrics["false_alarms"]))
    st.warning(t("about_small_test", n=n))
    matrix = REPORTS / "confusion_matrix.png"
    if matrix.is_file():
        st.image(str(matrix), caption=t("about_matrix_caption", n=n), width=520)

st.header(t("about_limits_heading"))
st.markdown(t("about_limits"))

st.header(t("about_credits_heading"))
st.markdown(t("about_credits"))
st.info(t("disclaimer"))
