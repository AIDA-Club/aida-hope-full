import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { About, aboutApi } from "../api";
import { CountUp, Em, Photo, Stamp } from "../components/ui";
import { useI18n } from "../i18n";

// Booth cards shown on the pinned photos. Card 17 is a real missed cancer (patient folder 1),
// so the "Missed by the model" stamp is true; card 4 is the background photo.
const FRONT_CARD = "17";
const BACK_CARD = "04";

export default function Home() {
  const { t, tn } = useI18n();
  const [about, setAbout] = useState<About | null>(null);
  useEffect(() => {
    aboutApi.get().then(setAbout).catch(() => setAbout(null));
  }, []);

  return (
    <section className="screen" id="home">
      <div className="hero">
        <div className="text">
          <div className="tagline"><span className="tag">{t("tag")}</span><span className="eyebrow">{t("home_eyebrow")}</span></div>
          <h1>
            {tn("home_h1_a", { pink: <span className="pink-word">{t("home_h1_pink")}</span> })}
            <br />
            <Em>{t("home_h1_b")}</Em>
          </h1>
          <p>{t("pink_intro")}</p>
        </div>
        <div className="stack" role="group" aria-label={t("home_stack")}>
          <div className="sheet" aria-hidden="true" />
          <Photo className="back" src={`/api/cards/${BACK_CARD}/original`} alt={t("home_case_back", { card: 4 })}
            tape={false} zoom={false} />
          <Photo className="front" src={`/api/cards/${FRONT_CARD}/original`} alt={t("home_case_front", { card: 17 })}
            caption={t("home_case_caption")} stamp={<Stamp>{t("stamp_missed")}</Stamp>} zoom={false} />
          <div className="sticky"><b>{t("home_sticky_title")}</b><br />{t("home_sticky")}</div>
          <img className="mascot" src="/pinkai/m-wave.webp" alt={t("mascot_wave_alt")} />
          <span className="hand">{t("home_mascot_hi").replace(/\s*[→←]\s*$/, "")}<span className="arrow" aria-hidden="true"> {t("home_mascot_hi").match(/[→←]/)?.[0] ?? ""}</span></span>
        </div>
      </div>

      <div className="sections">
        <Link to="/beat"><span className="ghost" aria-hidden="true">01</span><h2>{t("nav_beat")}</h2>
          <p>{t("home_s1_text")}</p><span className="small">{t("home_s1_small")}</span></Link>
        <Link to="/tweak"><span className="ghost" aria-hidden="true">02</span><h2>{t("nav_tweak")}</h2>
          <p>{t("home_s2_text")}</p><span className="small">{t("home_s2_small")}</span></Link>
        <Link to="/ask"><span className="ghost" aria-hidden="true">03</span><h2>{t("nav_ask")}</h2>
          <p>{t("home_s3_text")}</p><span className="small">{t("home_s3_small")}</span></Link>
      </div>

      {about && (
        <div className="result">
          <div className="big" dir="ltr">
            <CountUp to={about.caught} /><small>{t("home_of", { total: about.malignant_total })}</small>
            <svg viewBox="0 0 236 86" preserveAspectRatio="none" aria-hidden="true">
              <path d="M34 12C110 2 226 4 228 40c2 34-70 44-140 40C20 76 2 56 8 36c4-14 22-22 52-26" pathLength="1" fill="none" stroke="#C63D76" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
          <p className="result-text">
            {t("home_result", { n: about.n_test, missed: about.missed, alarms: about.false_alarms })}{" "}
            <span className="hl">{t("home_result_hl")}</span> {t("home_result_end")}
          </p>
          <Link className="help" to="/ask?topic=get_help">{t("home_help")}</Link>
        </div>
      )}
    </section>
  );
}
