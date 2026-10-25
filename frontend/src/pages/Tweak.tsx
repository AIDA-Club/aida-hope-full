import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Feature, Prediction, tweak, TweakModel } from "../api";
import { Icon } from "../components/Icon";
import { Btn, Em, ErrorBox, Loading, Note, Photo } from "../components/ui";
import { roundHalfEven } from "../format";
import { useI18n } from "../i18n";

const STEP = 0.01; // the Streamlit slider's float step

function useDebounced<T>(value: T, delay: number): T {
  const [current, setCurrent] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setCurrent(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return current;
}

const shown = (value: number) => (Math.abs(value) >= 1 ? value.toFixed(1) : value.toFixed(2));

export default function Tweak() {
  const { t } = useI18n();
  const [model, setModel] = useState<TweakModel | null>(null);
  const [error, setError] = useState<unknown>(null);
  const load = () => {
    setError(null);
    tweak.model().then(setModel).catch(setError);
  };
  useEffect(load, []);

  return (
    <section className="screen" id="tweak">
      <div className="tweak-head">
        <div>
          <h1 className="h1-step">{t("tweak_h1_a")} <Em>{t("tweak_h1_em")}</Em></h1>
          <p className="lead">{t("tweak_intro")}</p>
        </div>
        <span className="help static">{t("biopsy_note")}</span>
      </div>
      {error ? <ErrorBox error={error} onRetry={load} /> : !model ? <Loading /> : !model.available ? (
        <div className="card"><h2>{t("coming_soon")}</h2><p>{t("model_missing")}</p></div>
      ) : <Lab model={model} />}
    </section>
  );
}

function Lab({ model }: { model: TweakModel }) {
  const { t } = useI18n();
  const features = model.features!;
  const [values, setValues] = useState(() => features.map((feature) => feature.median));
  const [threshold, setThreshold] = useState(model.default_threshold ?? 0.5);
  const [last, setLast] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [error, setError] = useState<unknown>(null);

  const query = useDebounced(useMemo(() => ({ values, threshold }), [values, threshold]), 90);
  useEffect(() => {
    const controller = new AbortController();
    tweak.predict(query.values, query.threshold, controller.signal)
      .then((result) => { setPrediction(result); setError(null); })
      .catch((caught) => { if (!(caught instanceof DOMException)) setError(caught); });
    return () => controller.abort();
  }, [query]);

  const reset = (label: "benign" | "malignant") => {
    setValues([...model.presets![label]]);
    setThreshold(model.default_threshold ?? 0.5);
    setLast(null);
  };

  return (
    <>
      <p className="small model-note">{t("model_note")}</p>
      <div className="tweak">
        <div className="ledger sliders">
          <h3>{t("measurements")}</h3>
          {features.map((feature, index) => (
            <Slider key={feature.name} feature={feature} index={index} value={values[index]}
              onChange={(value) => {
                setValues((current) => current.map((old, i) => (i === index ? value : old)));
                setLast(feature.key);
              }} />
          ))}
          <div className="presets">
            <Btn variant="ghost" onClick={() => reset("benign")}>{t("preset_benign")}</Btn>
            <Btn variant="ghost" onClick={() => reset("malignant")}>{t("preset_malignant")}</Btn>
          </div>
        </div>

        {model.slide && <Microscope values={values} last={last} />}

        <div className="stack-gap">
          <div className="card output" aria-live="polite">
            <span className="eyebrow">{t("live_prediction_label")}</span>
            {error ? <ErrorBox error={error} /> : !prediction ? <Loading /> : <Output prediction={prediction} />}
          </div>
          <div className="ledger sliders threshold">
            <Slider threshold value={threshold} onChange={setThreshold} index={5}
              feature={{ name: "threshold", key: "decision_threshold", min: 0, max: 1, median: 0.5 }} />
            <p className="small">{t("threshold_trade")}</p>
            <p className="small">{t("threshold_note")}</p>
          </div>
        </div>
      </div>
    </>
  );
}

function Slider({ feature, value, onChange, index, threshold = false }:
  { feature: Feature; value: number; onChange: (value: number) => void; index: number; threshold?: boolean }) {
  const { t } = useI18n();
  const [help, setHelp] = useState(false);
  const id = useId();
  const label = threshold ? t("decision_threshold") : feature.key ? t(feature.key) : t("measurement_number", { number: index + 1 });
  const helpText = threshold ? t("threshold_note") : feature.key ? t(`${feature.key}_help`) : t("measurement_help");
  const ends = !threshold && feature.key ? t(`${feature.key}_ends`).split("|") : null;
  return (
    <div className="s">
      <div className="s-top">
        <label htmlFor={id}>{label}</label>
        {!threshold && (
          <button type="button" className="help-button" aria-expanded={help} aria-controls={`${id}-help`}
            aria-label={t("help_about", { name: label })} onClick={() => setHelp((open) => !open)}>
            <Icon name="help" size={18} />
          </button>
        )}
        <output htmlFor={id} dir="ltr">{threshold ? value.toFixed(2) : shown(value)}</output>
      </div>
      <p id={`${id}-help`} className="help-text" hidden={!help}>{helpText}</p>
      <input id={id} type="range" min={feature.min} max={feature.max} step={STEP} value={value}
        aria-valuetext={shown(value)} onChange={(event) => onChange(Number(event.target.value))} />
      {ends && ends.length === 2 && <div className="ends" aria-hidden="true"><span>{ends[0]}</span><span>{ends[1]}</span></div>}
    </div>
  );
}

function Microscope({ values, last }: { values: number[]; last: string | null }) {
  const { t } = useI18n();
  const url = tweak.slideUrl(useDebounced(values, 220));
  const [current, setCurrent] = useState(url);
  const [loading, setLoading] = useState(false);
  const pending = useRef(url);
  useEffect(() => {
    if (url === current) return;
    pending.current = url;
    setLoading(true);
    const image = new Image();
    image.onload = () => {
      if (pending.current === url) { setCurrent(url); setLoading(false); }
    };
    image.onerror = () => setLoading(false);
    image.src = url;
  }, [url, current]);

  return (
    <div className="microscope">
      <p className="small now" aria-live="polite">
        {last ? t("slide_now", { name: t(last), look: t(`${last}_look`) }) : t("slide_start")}
        {loading && <span className="sr-only"> {t("slide_loading")}</span>}
      </p>
      <div className="slide-wrap">
        <Photo src={current} alt={t("slide_heading")} tilt="r" caption={t("slide_cap")} className={loading ? "is-loading" : ""} />
        <img className="mascot magnify" src="/pinkai/m-magnify.webp" alt="" aria-hidden="true" />
      </div>
      <Note>{t("slide_note")}</Note>
      <p className="small">{t("slide_caption")}</p>
      <details className="compare">
        <summary>{t("slide_compare")}</summary>
        <div className="compare-grid">
          <Photo src="/api/tweak/reference/benign" alt={t("slide_real_benign")} caption={t("slide_real_benign")} tape={false} />
          <Photo src="/api/tweak/reference/malignant" alt={t("slide_real_malignant")} caption={t("slide_real_malignant")} tape={false} />
        </div>
      </details>
      <p className="tiny">{t("slide_credits")}</p>
    </div>
  );
}

function Output({ prediction }: { prediction: Prediction }) {
  const { t } = useI18n();
  const percent = prediction.confidence * 100;
  const bad = prediction.prediction === "malignant";
  return (
    <>
      <div className={`dial${bad ? " bad" : ""}`} style={{ "--p": `${percent}%` } as React.CSSProperties}
        role="img" aria-label={t("gauge_label", { prediction: t(prediction.prediction), percent })}>
        <div><div className="pct" dir="ltr">{roundHalfEven(percent, 0)}%</div><div className="lbl">{t(prediction.prediction)}</div></div>
      </div>
      <p className="small center">{t("dial_note")}</p>
      <div className="bars">
        {(["benign", "malignant"] as const).map((name) => (
          <div className="b" key={name}>
            <span>{t(name)}</span>
            <i role="progressbar" aria-label={t(name)} aria-valuemin={0} aria-valuemax={100}
              aria-valuenow={Math.round(prediction[name] * 100)}
              style={{ "--w": `${Math.max(prediction[name] * 100, 1)}%`, "--c": name === "benign" ? "var(--gold)" : "var(--rose)" } as React.CSSProperties} />
            <b dir="ltr">{roundHalfEven(prediction[name] * 100, 0)}%</b>
          </div>
        ))}
      </div>
      <p className="small">{t("gauge_note", { threshold: prediction.threshold * 100 })} · {t("gauge_probability_note")}</p>
    </>
  );
}
