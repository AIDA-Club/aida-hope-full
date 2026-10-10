import { useEffect, useState } from "react";
import { About as AboutData, aboutApi, CLASSES } from "../api";
import { Icon, IconName } from "../components/Icon";
import { Footer, Hero } from "../components/Shell";
import { Cta, ErrorBox, Loading } from "../components/ui";
import { roundHalfEven } from "../format";
import { useI18n } from "../i18n";

/** "- one\n- two" (the Markdown lists in i18n/*.json) as plain lines. */
const bullets = (text: string) => text.split("\n").map((line) => line.replace(/^- /, "").trim()).filter(Boolean);

export default function About() {
  const { t } = useI18n();
  const [data, setData] = useState<AboutData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const load = () => {
    setError(null);
    aboutApi.get().then(setData).catch(setError);
  };
  useEffect(load, []);

  return (
    <div className="page page-about">
      <Hero title={t("about_headline")} sub={t("about_sub")} mascot="/art/mascot-about-wave.webp"
        ribbon="/art/ribbon-about.webp" className="hero-about" />
      {error ? <ErrorBox error={error} onRetry={load} /> : !data ? <Loading /> : <Body data={data} />}
      <Footer />
    </div>
  );
}

function Body({ data }: { data: AboutData }) {
  const { t } = useI18n();
  const tiles: Array<{ value: string; label: string; icon: IconName; tone: string }> = [
    { value: String(data.n_test), label: t("about_metric_images"), icon: "image", tone: "pink" },
    { value: `${roundHalfEven(data.accuracy * 100, 0)}%`, label: t("metric_test_accuracy"), icon: "bars", tone: "lilac" },
    { value: `${data.caught} / ${data.malignant_total}`, label: t("metric_identified"), icon: "document", tone: "peach" },
    { value: String(data.false_alarms), label: t("metric_flagged"), icon: "warning", tone: "blue" },
  ];
  return (
    <>
      <div className="about-top">
        <section className="panel about-model tone-pink" aria-labelledby="model-title">
          <div className="about-model-text">
            <h2 id="model-title">{t("meet_model")}</h2>
            <p>{t("model_line_1")}</p>
            <p>{t("model_line_2")}</p>
            <p>{t("model_line_3")}</p>
          </div>
          <figure className="model-flow" aria-label={t("model_flow")}>
            {data.images.original && <img className="flow-img" src={data.images.original} alt={t("model_example")} />}
            <Icon name="arrow" className="flow-arrow" />
            <span className="flow-net"><img src="/art/illustration-neural-network.webp" alt="" /></span>
            <Icon name="arrow" className="flow-arrow" />
            <ul className="flow-labels">
              {CLASSES.map((label) => <li key={label} className={`label-${label}`}>{t(label).toLocaleLowerCase()}</li>)}
            </ul>
          </figure>
        </section>
        <section className="panel about-heatmap tone-lilac" aria-labelledby="heat-title">
          <div>
            <h2 id="heat-title">{t("heatmap_title")}</h2>
            <p>{t("heatmap_line_1")}</p>
            <p>{t("heatmap_line_2")}</p>
          </div>
          {data.images.heatmap && (
            <span className="heat-thumb"><img src={data.images.heatmap} alt={t("heatmap_example")} /></span>
          )}
        </section>
      </div>

      <h2 className="section-title">{t("results_context")}</h2>
      <ul className="metrics">
        {tiles.map((tile) => (
          <li key={tile.label} className={`metric tone-${tile.tone}`}>
            <div>
              <span className="metric-value" dir="ltr">{tile.value}</span>
              <span className="metric-label">{tile.label}</span>
            </div>
            <span className={`metric-icon icon-${tile.tone}`}><Icon name={tile.icon} size={44} />
              <span className={`badge-rays rays-${tile.tone}`} /></span>
          </li>
        ))}
      </ul>
      <div className="warning-strip" role="note">
        <span className="warning-badge"><Icon name="alert" /></span>
        <div>
          <p className="warning-title">{t("small_test_short")}</p>
          <p>{t("missed_line", { missed: data.missed, total: data.malignant_total })}</p>
          {data.booth_set && <p className="small-muted">{t("booth_set_note", { ...data.booth_set })}</p>}
        </div>
      </div>

      <div className="about-bottom">
        <section className="panel full-results" aria-labelledby="full-title">
          <h2 id="full-title">{t("read_full")}</h2>
          <details className="result-item">
            <summary><Icon name="document" />{t("confusion_matrix")}<Icon name="chevron" className="summary-chevron" /></summary>
            <div className="result-body">
              <Matrix data={data} />
              <p>{t("about_results_text", { n: data.n_test, accuracy: data.accuracy * 100, caught: data.caught,
                total: data.malignant_total, missed: data.missed, alarms: data.false_alarms })}</p>
              <p className="small-muted">{t("about_small_test", { n: data.n_test })}</p>
            </div>
          </details>
          <details className="result-item">
            <summary><Icon name="bars" />{t("split_title")}<Icon name="chevron" className="summary-chevron" /></summary>
            <div className="result-body">
              <ul className="split-list">
                <li><strong dir="ltr">{data.split_sizes.train}</strong> {t("split_train")}</li>
                <li><strong dir="ltr">{data.split_sizes.val}</strong> {t("split_val")}</li>
                <li><strong dir="ltr">{data.split_sizes.test}</strong> {t("split_test")}</li>
              </ul>
              <p>{t("about_model_text", { ...data.split_sizes })}</p>
            </div>
          </details>
          <details className="result-item">
            <summary><Icon name="book" />{t("refs_title")}<Icon name="chevron" className="summary-chevron" /></summary>
            <div className="result-body">
              <ul className="refs">{bullets(t("about_credits")).map((line) => <li key={line}>{line}</li>)}</ul>
            </div>
          </details>
        </section>
        <section className="panel limits tone-pink" aria-labelledby="limits-title">
          <img className="limits-mascot" src="/art/mascot-about-explore.webp" alt="" aria-hidden="true" />
          <div className="limits-text">
            <h2 id="limits-title">{t("limits_title")}</h2>
            <ul>{bullets(t("about_limits")).map((line) => <li key={line}>{line}</li>)}</ul>
            <Cta to="/" arrow="plain" className="cta-pill">{t("explore_activities")}</Cta>
          </div>
        </section>
      </div>
    </>
  );
}

/** The confusion matrix from metrics.json as a real table (the PNG is offered too). */
function Matrix({ data }: { data: AboutData }) {
  const { t } = useI18n();
  const { rows_truth_cols_pred: labels, matrix } = data.confusion_matrix;
  return (
    <>
      <table className="matrix">
        <caption>{t("about_matrix_caption", { n: data.n_test })}</caption>
        <thead>
          <tr><th scope="col">{t("matrix_truth")} ↓ / {t("matrix_pred")} →</th>
            {labels.map((label) => <th key={label} scope="col">{t(label)}</th>)}</tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th scope="row">{t(labels[i])}</th>
              {row.map((count, j) => <td key={j} className={i === j ? "diag" : count ? "miss" : ""}>{count}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {data.images["confusion-matrix"] && (
        <a className="link-button" href={data.images["confusion-matrix"]} target="_blank" rel="noreferrer">
          {t("confusion_matrix")} (PNG)
        </a>
      )}
    </>
  );
}
