import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Feature, Prediction, tweak, TweakModel } from "../api";
import { Icon } from "../components/Icon";
import { Footer, Hero } from "../components/Shell";
import { ErrorBox, Loading } from "../components/ui";
import { roundHalfEven } from "../format";
import { useI18n } from "../i18n";

const STEP = 0.01; // the Streamlit slider's float step

function show(value: number) {
  return value.toFixed(2);
}

function useDebounced<T>(value: T, delay: number): T {
  const [current, setCurrent] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setCurrent(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return current;
}

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
    <div className="page page-tweak">
      <Hero title={t("tweak_title")} sub={t("tweak_intro")} mascot="/art/mascot-tweak-thinking-wink.webp"
        ribbon="/art/ribbon-tweak.webp" className="hero-tweak">
        {model?.available && <p className="note-blue note-wide"><Icon name="info" />{t("model_note")}</p>}
      </Hero>
      {error ? <ErrorBox error={error} onRetry={load} /> : !model ? <Loading /> : !model.available ? (
        <section className="panel coming-soon">
          <h2>{t("coming_soon")}</h2>
          <p>{t("model_missing")}</p>
        </section>
      ) : <Lab model={model} />}
      <Footer credits={<><strong>{t("credits_label")}</strong> {t("credits_short")}</>} />
    </div>
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
    setThreshold(0.5);
    setLast(null);
  };

  return (
    <>
      <div className="reset-row">
        <button type="button" className="reset-button" onClick={() => reset("benign")}>
          <Icon name="leaf" />{t("reset_benign")}
        </button>
        <button type="button" className="reset-button" onClick={() => reset("malignant")}>
          <Icon name="cell" />{t("reset_malignant")}
        </button>
      </div>
      <div className="lab">
        <section className="panel lab-col lab-sliders" aria-labelledby="measure-title">
          <header className="lab-head">
            <span className="lab-icon"><Icon name="tools" size={30} /></span>
            <div>
              <h2 id="measure-title">{t("feature_controls")}</h2>
              <p>{t("tweak_explore_sub")}</p>
            </div>
          </header>
          {features.map((feature, index) => (
            <Slider key={feature.name} feature={feature} value={values[index]} index={index}
              onChange={(value) => {
                setValues((current) => current.map((old, i) => (i === index ? value : old)));
                setLast(feature.key);
              }} />
          ))}
          <Slider threshold value={threshold} onChange={setThreshold}
            feature={{ name: "threshold", key: "decision_threshold", min: 0, max: 1, median: 0.5 }} index={5} />
          <p className="tiny tradeoff">{t("threshold_tradeoff")}</p>
        </section>

        {model.slide && <Microscope values={values} last={last} />}

        <section className="panel lab-col lab-output" aria-labelledby="output-title" aria-live="polite">
          <header className="lab-head">
            <span className="lab-icon"><Icon name="bars" size={30} /></span>
            <div>
              <h2 id="output-title">{t("live_output")}</h2>
              <p>{t("live_output_sub")}</p>
            </div>
          </header>
          {error ? <ErrorBox error={error} /> : !prediction ? <Loading /> : <Output prediction={prediction} />}
        </section>
      </div>
      <section className="panel howto" aria-labelledby="howto-title">
        <div className="howto-intro">
          <Icon name="book" size={44} />
          <div>
            <h2 id="howto-title">{t("how_read")}</h2>
            <p>{t("how_read_sub")}</p>
          </div>
        </div>
        <ol className="howto-steps">
          <li><span className="howto-n">1</span><p>{t("how_1")}</p></li>
          <li><span className="howto-n">2</span><p>{t("how_2")}</p></li>
          <li><span className="howto-n">3</span><p>{t("biopsy_note")}</p></li>
          <li><span className="howto-n howto-gear"><Icon name="gear" /></span><p>{t("threshold_note")}</p></li>
        </ol>
      </section>
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
  const fill = ((value - feature.min) / (feature.max - feature.min)) * 100;
  return (
    <div className={`slider${threshold ? " slider-threshold" : ""}`}>
      <div className="slider-top">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id} className="slider-value" dir="ltr">{show(value)}</output>
        <button type="button" className="help-button" aria-expanded={help} aria-controls={`${id}-help`}
          aria-label={t("slider_help", { name: label })} onClick={() => setHelp((open) => !open)}>
          <Icon name="help" size={20} />
        </button>
      </div>
      <p id={`${id}-help`} className="help-text" hidden={!help}>{helpText}</p>
      <input id={id} type="range" min={feature.min} max={feature.max} step={STEP} value={value}
        style={{ "--fill": `${fill}%` } as React.CSSProperties}
        aria-describedby={help ? `${id}-help` : undefined} aria-valuetext={show(value)}
        onChange={(event) => onChange(Number(event.target.value))} />
    </div>
  );
}

function Microscope({ values, last }: { values: number[]; last: string | null }) {
  const { t } = useI18n();
  const url = tweak.slideUrl(useDebounced(values, 220));
  const [shown, setShown] = useState(url);
  const [loading, setLoading] = useState(false);
  const pending = useRef(url);
  useEffect(() => {
    if (url === shown) return;
    pending.current = url;
    setLoading(true);
    const image = new Image();
    image.onload = () => {
      if (pending.current === url) { setShown(url); setLoading(false); }
    };
    image.onerror = () => setLoading(false);
    image.src = url;
  }, [url, shown]);

  return (
    <section className="panel lab-col lab-micro" aria-labelledby="micro-title">
      <header className="lab-head">
        <span className="lab-icon"><Icon name="microscope" size={30} /></span>
        <div>
          <h2 id="micro-title">{t("slide_heading")}</h2>
          <p aria-live="polite">{last ? t("slide_now", { name: t(last), look: t(`${last}_look`) }) : t("slide_start")}</p>
        </div>
      </header>
      <div className={`micro-frame${loading ? " is-loading" : ""}`}>
        <img src={shown} alt={t("slide_heading")} />
        {loading && <span className="sr-only">{t("slide_loading")}</span>}
      </div>
      <p className="tiny">{t("slide_caption")}</p>
      <details className="compare-details">
        <summary><Icon name="chevron" size={18} />{t("slide_compare")}</summary>
        <div className="compare-grid">
          <figure><img src="/api/tweak/reference/benign" alt={t("slide_real_benign")} /><figcaption>{t("slide_real_benign")}</figcaption></figure>
          <figure><img src="/api/tweak/reference/malignant" alt={t("slide_real_malignant")} /><figcaption>{t("slide_real_malignant")}</figcaption></figure>
        </div>
      </details>
      <p className="tiny">{t("slide_credits")}</p>
    </section>
  );
}

function Output({ prediction }: { prediction: Prediction }) {
  const { t } = useI18n();
  const percent = prediction.confidence * 100;
  const radius = 92;
  const circumference = 2 * Math.PI * radius;
  const label = t(prediction.prediction);
  return (
    <div className="output">
      <div className="gauge" role="img" aria-label={t("gauge_label", { prediction: label, percent })}>
        <svg viewBox="0 0 220 220" aria-hidden="true">
          <circle cx="110" cy="110" r={radius} className="gauge-track" />
          <circle cx="110" cy="110" r={radius} className="gauge-fill"
            strokeDasharray={`${(percent / 100) * circumference} ${circumference}`} />
        </svg>
        <div className="gauge-center" aria-hidden="true">
          <span className="gauge-number" dir="ltr">{roundHalfEven(percent, 0)}%</span>
          <span className="gauge-label">{label}</span>
        </div>
      </div>
      <p className="tiny">{t("gauge_probability_note")}</p>
      <div className="prob-list">
        {(["malignant", "benign"] as const).map((name) => (
          <div key={name} className="prob">
            <div className="prob-label">{t("confidence", { label: t(name), percent: prediction[name] * 100 })}</div>
            <div className="prob-track" role="progressbar" aria-label={t(name)} aria-valuemin={0} aria-valuemax={100}
              aria-valuenow={Math.round(prediction[name] * 100)}>
              <div className="prob-fill" style={{ width: `${Math.max(prediction[name] * 100, 1.5)}%` }} />
            </div>
          </div>
        ))}
      </div>
      <p className="tiny">{t("gauge_note", { threshold: prediction.threshold * 100 })}</p>
      <p className="tiny">{t("health_note")}</p>
    </div>
  );
}
