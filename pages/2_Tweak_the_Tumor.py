import html

import streamlit as st

import slide_image
from booth import BoothError, ROOT, load_class_medians, load_model_bundle, malignant_probability, t

FRIENDLY_FEATURES = {"mean radius": "nucleus_size", "mean texture": "texture",
                     "mean smoothness": "smoothness", "mean concavity": "concavity",
                     "worst concave points": "concave_points"}


def reset_measurements(features: list[dict], medians: dict, label: str) -> None:
    for feature in features[:5]:
        st.session_state[f"feature_{feature['name']}"] = float(medians[label][feature["name"]])
    st.session_state["decision_threshold"] = 0.5
    st.session_state.pop("tweak_last", None)


def remember(friendly: str | None) -> None:
    st.session_state["tweak_last"] = friendly


@st.cache_data(show_spinner=False, max_entries=256)
def slide_jpeg(look: slide_image.Look) -> bytes:
    return slide_image.render_jpeg(look)


def slide_view(features: list[dict], values: list[float], medians: dict) -> None:
    """The real microscope image, reshaped to match the current slider values."""
    names = [feature["name"] for feature in features]
    if not set(slide_image.FEATURES) <= set(names):
        return  # a different model: no matching picture
    current = dict(zip(names, values))
    specs = {feature["name"]: feature for feature in features}
    look = slide_image.look_for(current, specs, medians["benign"])
    with st.container(key="slide_view"):
        st.subheader(t("slide_heading"))
        st.image(slide_jpeg(look), width="stretch")
        last = st.session_state.get("tweak_last")
        if last:
            st.markdown(f"**{html.escape(t('slide_now', name=t(last), look=t(last + '_look')))}**")
        else:
            st.markdown(f"**{html.escape(t('slide_start'))}**")
    st.caption(t("slide_caption"))
    with st.expander(t("slide_compare")):
        benign, malignant = st.columns(2)
        benign.image(str(slide_image.SLIDE / "base.jpg"), caption=t("slide_real_benign"), width="stretch")
        malignant.image(str(slide_image.SLIDE / "reference_malignant.jpg"), caption=t("slide_real_malignant"),
                        width="stretch")
    st.caption(t("slide_credits"))

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
    slide_slot = st.container()  # filled after the sliders, so it shows their current values
    st.subheader(t("feature_controls"))
    for index, feature in enumerate(features[:5]):
        friendly = FRIENDLY_FEATURES.get(feature["name"])
        label = t(friendly) if friendly else t("measurement_number", number=index + 1)
        help_text = t(f"{friendly}_help") if friendly else t("measurement_help")
        widget_key = f"feature_{feature['name']}"
        values[index] = st.slider(label, min_value=float(feature["min"]), max_value=float(feature["max"]),
                                  value=None if widget_key in st.session_state else float(feature["median"]),
                                  help=help_text, key=widget_key, on_change=remember, args=(friendly,))
    threshold = st.slider(t("decision_threshold"), 0.0, 1.0,
                          None if "decision_threshold" in st.session_state else 0.5,
                          0.01, key="decision_threshold")
    st.caption(t("threshold_note"))
    st.write(t("threshold_tradeoff"))
    with slide_slot:
        slide_view(features, values, medians)

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
