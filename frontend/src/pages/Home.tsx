import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { homeApi } from "../api";
import { Icon } from "../components/Icon";
import { Footer, Hero } from "../components/Shell";
import { Cta, IconBadge } from "../components/ui";
import { useI18n } from "../i18n";

export default function Home() {
  const { t, tn } = useI18n();
  const [cards, setCards] = useState<string[]>([]);
  useEffect(() => {
    homeApi.get().then((home) => setCards(home.cards)).catch(() => setCards([]));
  }, []);

  return (
    <div className="page page-home">
      <Hero
        className="hero-home"
        title={<>
          <span className="line">{tn("home_headline_1", { pink: <span className="title-pink">{t("home_headline_pink")}</span> })}</span>{" "}
          <span className="line">{t("home_headline_2")}</span>
        </>}
        sub={t("home_sub")}
        mascot="/art/mascot-wave.webp"
        ribbon="/art/ribbon-home.webp"
      >
        <Cta size="lg" className="hero-cta" onClick={() => document.getElementById("activities")?.scrollIntoView({ behavior: "smooth" })}>
          {t("home_cta")}
        </Cta>
      </Hero>

      <section id="activities" className="panel activity-panel" aria-label={t("home_activities")}>
        <article className="activity activity-pink">
          <header className="activity-head">
            <IconBadge icon="search" tone="pink" size="lg" />
            <div>
              <h2>{t("public_challenge_title")}</h2>
              <p>{t("home_beat_text")}</p>
            </div>
          </header>
          <div className="activity-art art-ultrasound" aria-hidden="true">
            <span className="art-blob" />
            <img className="art-rays" src="/art/decoration-three-rays.webp" alt="" />
            {cards.length === 3 && (
              <div className="us-stack">
                <img className="us us-left" src={cards[1]} alt="" />
                <img className="us us-right" src={cards[2]} alt="" />
                <img className="us us-front" src={cards[0]} alt="" />
              </div>
            )}
          </div>
          <Cta to="/beat">{t("home_beat_cta")}</Cta>
        </article>

        <article className="activity activity-lilac">
          <header className="activity-head">
            <IconBadge icon="sliders" tone="lilac" size="lg" />
            <div>
              <h2>{t("tweak_title")}</h2>
              <p>{t("home_tweak_text")}</p>
            </div>
          </header>
          <div className="activity-art art-tweak" aria-hidden="true">
            <img className="art-sliders" src="/art/illustration-measurement-sliders.webp" alt="" />
            <img className="art-chart" src="/art/illustration-bar-chart.webp" alt="" />
          </div>
          <Cta to="/tweak">{t("home_tweak_cta")}</Cta>
        </article>

        <article className="activity activity-peach">
          <header className="activity-head">
            <IconBadge icon="question" tone="peach" size="lg" />
            <div>
              <h2>{t("ask_title")}</h2>
              <p>{t("home_ask_text")}</p>
            </div>
          </header>
          <div className="activity-art art-ask" aria-hidden="true">
            <span className="art-blob art-blob-peach" />
            <img className="art-chat-pink" src="/art/illustration-chat-pink.webp" alt="" />
            <img className="art-chat-lilac" src="/art/illustration-chat-lilac.webp" alt="" />
            <img className="art-question" src="/art/illustration-question-disc.webp" alt="" />
          </div>
          <Cta to="/ask">{t("home_ask_cta")}</Cta>
        </article>
      </section>

      <Footer extra={<Link to="/about" className="behind-link">{t("behind_demo")} <Icon name="arrow" size={18} /></Link>} />
    </div>
  );
}
