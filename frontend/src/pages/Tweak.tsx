import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Feature, Prediction, tweak, TweakModel } from "../api";
import { Icon } from "../components/Icon";
import { Btn, Em, ErrorBox, Loading, Note } from "../components/ui";
import { useI18n } from "../i18n";
import { drawCell } from "./cell";

// The design's slider steps and number formats, per feature (radius, texture, smoothness,
// concavity, worst concave points); other models fall back to the Streamlit step.
const STEPS = [0.1, 0.1, 0.001, 0.002, 0.001];
const DIGITS = [1, 1, 3, 3, 3];

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
  const cell = useRef<HTMLCanvasElement>(null);
  const mini = useRef<HTMLCanvasElement>(null);

  // The model's answer always comes from the API (the trained scikit-learn pipeline).
  const query = useDebounced(useMemo(() => ({ values, threshold }), [values, threshold]), 60);
  useEffect(() => {
    const controller = new AbortController();
    tweak.predict(query.values, query.threshold, controller.signal)
      .then((result) => { setPrediction(result); setError(null); })
      .catch((caught) => { if (!(caught instanceof DOMException)) setError(caught); });
    return () => controller.abort();
  }, [query]);

  // The microscope illustration is drawn in the browser straight from the slider values.
  const drawable = model.slide && features.length >= 5;
  useEffect(() => {
    if (drawable && cell.current) drawCell(cell.current, values, mini.current);
  }, [values, drawable]);

  const reset = (label: "benign" | "malignant") => {
    setValues([...model.presets![label]]);
    setThreshold(model.default_threshold ?? 0.5);
    setLast(null);
  };
  const chance = prediction ? Math.round(prediction.malignant * 100) : null;
  const bad = prediction?.prediction === "malignant";

  return (
    <>
      {drawable && (
        <div className={`live-mini${bad ? " bad" : ""}`} aria-hidden="true">
          <div className="frame">
            <canvas ref={mini} width={1140} height={980} />
            <div className="badge">
              <b id="mini-pct" dir="ltr">{chance ?? "–"}%</b>
              <span>{t("mini_chance")}</span>
              <span className="call">{t("mini_call")}<b>{prediction ? t(prediction.prediction) : "…"}</b></span>
              <i id="mini-bar" style={{ "--p": `${chance ?? 0}%` } as React.CSSProperties} />
            </div>
          </div>
        </div>
      )}
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

        <div className="microscope">
          <p className="small now" aria-live="polite">
            {last ? t("slide_now", { name: t(last), look: t(`${last}_look`) }) : t("slide_start")}
          </p>
          {drawable && (
            <figure className="photo tilt-r cell-photo">
              <div className="tape-bit" aria-hidden="true" />
              <canvas ref={cell} width={1140} height={980} role="img" aria-label={t("cell_alt")} />
              <figcaption className="cap">{t("slide_cap")}</figcaption>
            </figure>
          )}
          <img className="mascot" src="/pinkai/m-magnify.webp" alt="" aria-hidden="true" />
          <Note>{t("slide_note")}</Note>
          <p className="small">{t("slide_caption")}</p>
          <details className="compare">
            <summary>{t("slide_compare")}</summary>
            <div className="compare-grid">
              <figure className="compare-fig"><img src="/api/tweak/reference/benign" alt={t("slide_real_benign")} /><figcaption>{t("slide_real_benign")}</figcaption></figure>
              <figure className="compare-fig"><img src="/api/tweak/reference/malignant" alt={t("slide_real_malignant")} /><figcaption>{t("slide_real_malignant")}</figcaption></figure>
            </div>
          </details>
          <p className="tiny">{t("slide_credits")}</p>
        </div>

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
  const digits = threshold ? 2 : DIGITS[index] ?? 2;
  const shown = value.toFixed(digits);
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
        <output htmlFor={id} dir="ltr">{shown}</output>
      </div>
      <p id={`${id}-help`} className="help-text" hidden={!help}>{helpText}</p>
      <input id={id} type="range" min={feature.min} max={feature.max} step={threshold ? 0.01 : STEPS[index] ?? 0.01}
        value={value} aria-valuetext={shown} onChange={(event) => onChange(Number(event.target.value))} />
      {ends && ends.length === 2 && <div className="ends" aria-hidden="true"><span>{ends[0]}</span><span>{ends[1]}</span></div>}
    </div>
  );
}

function Output({ prediction }: { prediction: Prediction }) {
  const { t } = useI18n();
  const chance = Math.round(prediction.malignant * 100);
  const bad = prediction.prediction === "malignant";
  const call = useRef<HTMLElement>(null);
  const previous = useRef(prediction.prediction);
  useEffect(() => {
    // the model's call pops when it flips
    if (previous.current !== prediction.prediction && call.current) {
      call.current.classList.remove("flip");
      void call.current.offsetWidth;
      call.current.classList.add("flip");
    }
    previous.current = prediction.prediction;
  }, [prediction.prediction]);
  return (
    <>
      <div className={`dial${bad ? " bad" : ""}`} id="dial" style={{ "--p": `${chance}%` } as React.CSSProperties}
        role="img" aria-label={t("gauge_label", { prediction: t("malignant"), percent: prediction.malignant * 100 })}>
        <div><div className="pct" dir="ltr">{chance}%</div><div className="lbl">{t("dial_label")}</div></div>
      </div>
      <p className="small center">
        {t("dial_call")} <b id="call" ref={call}>{t(prediction.prediction)}</b><br />{t("dial_rule")}
      </p>
      <div className="bars">
        {(["benign", "malignant"] as const).map((name) => (
          <div className="b" key={name}>
            <span>{t(name)}</span>
            <i role="progressbar" aria-label={t(name)} aria-valuemin={0} aria-valuemax={100}
              aria-valuenow={Math.round(prediction[name] * 100)}
              style={{ "--w": `${Math.max(prediction[name] * 100, 1)}%`, "--c": name === "benign" ? "var(--gold)" : "var(--rose)" } as React.CSSProperties} />
            <b dir="ltr">{Math.round(prediction[name] * 100)}%</b>
          </div>
        ))}
      </div>
      <p className="small">{t("gauge_note", { threshold: prediction.threshold * 100 })}</p>
    </>
  );
}
