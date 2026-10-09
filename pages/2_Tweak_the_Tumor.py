import html

import streamlit as st

from booth import BoothError, ROOT, load_class_medians, load_model_bundle, malignant_probability, t

FRIENDLY_FEATURES = {"mean radius": "nucleus_size", "mean texture": "texture",
                     "mean smoothness": "smoothness", "mean concavity": "concavity",
                     "worst concave points": "concave_points"}


def reset_measurements(features: list[dict], medians: dict, label: str) -> None:
    for feature in features[:5]:
        st.session_state[f"feature_{feature['name']}"] = float(medians[label][feature["name"]])
    st.session_state["decision_threshold"] = 0.5

st.title(t("tweak_title"))
st.write(t("tweak_intro"))
files = (ROOT / "models" / "wdbc_model.pkl", ROOT / "models" / "wdbc_features.json")
if not all(file.is_file() for file in files):
    st.info(t("coming_soon"))
    st.write(t("model_missing"))
    st.stop()

try:
    model, features, labels = load_model_bundle()
    medians = load_class_medians(features)
except BoothError as exc:
    st.error(exc.ui_message())
    st.stop()
except Exception:
    st.error(t("model_invalid"))
    st.stop()

st.info(t("model_note"))
benign, malignant = st.columns(2)
benign.button(t("reset_benign"), key="reset_benign", width="stretch",
              on_click=reset_measurements, args=(features, medians, "benign"))
malignant.button(t("reset_malignant"), key="reset_malignant", width="stretch",
                 on_click=reset_measurements, args=(features, medians, "malignant"))
controls, display = st.columns([1.1, 1], gap="large")
values = [float(feature["median"]) for feature in features]
with controls:
    st.subheader(t("feature_controls"))
    for index, feature in enumerate(features[:5]):
        friendly = FRIENDLY_FEATURES.get(feature["name"])
        label = t(friendly) if friendly else t("measurement_number", number=index + 1)
        help_text = t(f"{friendly}_help") if friendly else t("measurement_help")
        widget_key = f"feature_{feature['name']}"
        values[index] = st.slider(label, min_value=float(feature["min"]), max_value=float(feature["max"]),
                                  value=None if widget_key in st.session_state else float(feature["median"]),
                                  help=help_text, key=widget_key)
    threshold = st.slider(t("decision_threshold"), 0.0, 1.0,
                          None if "decision_threshold" in st.session_state else 0.5,
                          0.01, key="decision_threshold")
    st.caption(t("threshold_note"))
    st.write(t("threshold_tradeoff"))

with display:
    try:
        probability = malignant_probability(model, values, labels)
    except Exception:
        st.error(t("model_prediction_error"))
        st.stop()
    prediction = "malignant" if probability >= threshold else "benign"
    confidence = probability if prediction == "malignant" else 1 - probability
    st.subheader(t("live_prediction", prediction=t(prediction)))
    st.markdown(f'<div class="booth-gauge" role="img" aria-label="{html.escape(t("gauge_label", prediction=t(prediction), percent=100 * confidence), quote=True)}" '
                f'style="background:conic-gradient(#C63D76 {100 * confidence:.3f}%, #EFDDE5 0)">'
                f'<div class="booth-gauge-center"><div class="booth-gauge-number">{confidence:.0%}</div>'
                f'<div class="booth-gauge-label">{html.escape(t(prediction))}</div></div></div>',
                unsafe_allow_html=True)
    st.caption(t("gauge_probability_note"))
    st.progress(probability, text=t("confidence", label=t("malignant"), percent=100 * probability))
    st.progress(1 - probability, text=t("confidence", label=t("benign"), percent=100 * (1 - probability)))
    st.caption(t("gauge_note", threshold=threshold * 100))

st.write(t("biopsy_note"))
