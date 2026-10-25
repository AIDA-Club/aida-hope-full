import { useEffect, useState } from "react";
import { About as AboutData, aboutApi } from "../api";
import { bullets, CountUp, Em, ErrorBox, Loading, Note } from "../components/ui";
import { roundHalfEven } from "../format";
import { useI18n } from "../i18n";

/** Every number on this page comes from data/reports/metrics.json via the API. */
export default function About() {
  const { t } = useI18n();
  const [data, setData] = useState<AboutData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const load = () => {
    setError(null);
    aboutApi.get().then(setData).catch(setError);
  };
  useEffect(load, []);
  if (error) return <section className="screen"><ErrorBox error={error} onRetry={load} /></section>;
  if (!data) return <section className="screen"><Loading /></section>;

  const counts = data.test_counts ?? { normal: 0, benign: 0, malignant: 0 };
  const share = (n: number, total: number) => `${(n / total) * 100}%`;
  const nonCancer = counts.normal + counts.benign;
  const sizes = data.split_sizes;
  const splitTotal = sizes.train + sizes.val + sizes.test;
  const { rows_truth_cols_pred: labels, matrix } = data.confusion_matrix;
  const malignantIndex = labels.indexOf("malignant");
  // Cell styles from the design: correct calls share one quiet colour; the two kinds of mistake
  // (false alarms: benign → malignant, missed cancers: malignant → benign) are the solid fills.
  const cellClass = (i: number, j: number) =>
    i === j ? "ok"
      : labels[i] === "benign" && j === malignantIndex ? "fa"
      : i === malignantIndex && labels[j] === "benign" ? "miss" : "";
  const missedToBenign = matrix[malignantIndex]?.[labels.indexOf("benign")] ?? data.missed;

  return (
    <section className="screen" id="about">
      <div className="about-head">
        <div>
          <h1 className="h1-step">{t("about_h1_a")} <Em>{t("about_h1_em")}</Em></h1>
          <p className="lead">{t("about_intro")}</p>
        </div>
        <ul className="tiles">
          <li className="card tile">
            <div className="k">{t("tile_images")}</div><div className="v" dir="ltr"><CountUp to={data.n_test} /></div>
            <div className="bar" aria-hidden="true">
              <span style={{ width: share(counts.normal, data.n_test), background: "var(--green)" }} />
              <span style={{ width: share(counts.benign, data.n_test), background: "var(--gold)" }} />
              <span style={{ width: share(counts.malignant, data.n_test), background: "var(--rose)" }} />
            </div>
            <div className="small">{t("tile_images_small", { normal: counts.normal, benign: counts.benign, malignant: counts.malignant })}</div>
          </li>
          <li className="card tile">
            <div className="k">{t("tile_accuracy")}</div><div className="v" dir="ltr">{roundHalfEven(data.accuracy * 100, 0)}%</div>
            <div className="bar" aria-hidden="true"><span style={{ width: `${data.accuracy * 100}%`, background: "var(--rose)" }} /></div>
            <div className="small">{t("tile_accuracy_small")}</div>
          </li>
          <li className="card tile">
            <div className="k">{t("tile_caught")}</div>
            <div className="v" dir="ltr">{data.caught} <small>{t("home_of", { total: data.malignant_total })}</small></div>
            <div className="bar" aria-hidden="true"><span style={{ width: share(data.caught, data.malignant_total), background: "var(--rose)" }} /></div>
            <div className="small">{t("tile_caught_small", { missed: data.missed })}</div>
          </li>
          <li className="card tile">
            <div className="k">{t("tile_alarms")}</div><div className="v" dir="ltr">{data.false_alarms}</div>
            <div className="bar" aria-hidden="true"><span style={{ width: share(data.false_alarms, nonCancer || 1), background: "var(--gold)" }} /></div>
            <div className="small">{t("tile_alarms_small", { n: nonCancer })}</div>
          </li>
        </ul>
      </div>

      <div className="cols">
        <div className="col">
          <h2>{t("the_model")}</h2>
          <p className="body">{t("about_model_text", { ...sizes })}</p>
          <div className="split" aria-hidden="true">
            <span style={{ width: share(sizes.train, splitTotal), background: "var(--plum)" }} />
            <span style={{ width: share(sizes.val, splitTotal), background: "var(--rose)" }} />
            <span style={{ width: share(sizes.test, splitTotal), background: "var(--gold)" }} />
          </div>
          <div className="legend">
            <span><b>{sizes.train}</b> {t("split_train")}</span><span><b>{sizes.val}</b> {t("split_val")}</span>
            <span><b>{sizes.test}</b> {t("split_test")}</span>
          </div>
          <div className="mascot-note bottom">
            <img className="mascot" src="/pinkai/m-clipboard.webp" alt={t("mascot_clipboard_alt")} />
            <span className="hand">{t("about_mascot_note")}</span>
          </div>
        </div>

        <div className="col">
          <h2>{t("right_wrong")}</h2>
          <table className="matrix">
            <caption className="sr-only">{t("about_matrix_caption", { n: data.n_test })}</caption>
            <thead><tr><td />{labels.map((label) => <th key={label} scope="col" className="h">{t(label)}</th>)}</tr></thead>
            <tbody>
              {matrix.map((row, i) => (
                <tr key={labels[i]}>
                  <th scope="row" className="r">{t(labels[i])}</th>
                  {row.map((count, j) => <td key={j} className={`c ${cellClass(i, j)}`}
                    style={{ "--d": `${0.5 + (i * row.length + j) * 0.06}s` } as React.CSSProperties}>{count}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small">
            {t("matrix_legend")} · <span className="gold">{t("matrix_alarms", { n: data.false_alarms })}</span> ·{" "}
            <span className="rose">{t("matrix_missed", { n: data.missed })}</span>
          </p>
          <p className="small">{t("about_results_text", { n: data.n_test, accuracy: data.accuracy * 100, caught: data.caught,
            total: data.malignant_total, missed: data.missed, alarms: data.false_alarms })}</p>
          <p className="small">{t("about_small_test", { n: data.n_test })}</p>
          {data.booth_set && <p className="small">{t("booth_set_note", { ...data.booth_set })}</p>}
          {missedToBenign > 0 && <div className="quote bottom">{t("matrix_quote")}</div>}
        </div>

        <div className="col">
          <h2>{t("limits")}</h2>
          <ul className="limits">{bullets(t("about_limits")).map((line) => <li key={line}>{line}</li>)}</ul>
          <Note>{t("club_note")}</Note>
          <div className="bottom credits">
            <div className="eyebrow">{t("credits")}</div>
            {bullets(t("about_credits")).map((line) => <p key={line} className="small">{line}</p>)}
          </div>
        </div>
      </div>
    </section>
  );
}
