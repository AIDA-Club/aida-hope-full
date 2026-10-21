import { FormEvent, useCallback, useEffect, useId, useState } from "react";
import { challenge, ChallengeInfo, CLASSES, ClassName, Folder, Round } from "../api";
import { Icon } from "../components/Icon";
import { Footer, Hero } from "../components/Shell";
import { Cta, ErrorBox, errorText, IconBadge, Loading, ProbabilityBar, Toggle, ZoomImage } from "../components/ui";
import { useI18n } from "../i18n";

type Action = () => Promise<{ round: Round | null }>;

export default function Beat() {
  const [round, setRound] = useState<Round | null | undefined>(undefined);
  const [info, setInfo] = useState<ChallengeInfo | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([challenge.round(), challenge.info()])
      .then(([reply, details]) => {
        setRound(reply.round);
        setInfo(details);
      })
      .catch(setError);
  }, []);
  useEffect(load, [load]);

  /** Run one server step; the server decides what the visitor may see next. */
  const act = useCallback(async (action: Action) => {
    setBusy(true);
    setError(null);
    try {
      const reply = await action();
      setRound(reply.round);
      window.scrollTo(0, 0);
    } catch (caught) {
      setError(caught);
      throw caught;
    } finally {
      setBusy(false);
    }
  }, []);

  if (round === undefined) return <div className="page">{error ? <ErrorBox error={error} onRetry={load} /> : <Loading />}</div>;
  if (round === null) return <Intro info={info} act={act} busy={busy} />;
  if (round.phase === "end") return <End round={round} info={info} act={act} busy={busy} error={error} />;
  return <Play round={round} act={act} busy={busy} error={error} setRound={setRound} />;
}

// ---------------------------------------------------------------------------
// 1 · Introduction
// ---------------------------------------------------------------------------
function Intro({ info, act, busy }: { info: ChallengeInfo | null; act: (a: Action) => Promise<void>; busy: boolean }) {
  const { t } = useI18n();
  const size = info?.round_size ?? 5;
  const [card, setCard] = useState("");
  const [cardError, setCardError] = useState<string | null>(null);
  const [startError, setStartError] = useState<unknown>(null);
  const inputId = useId();
  const errorId = useId();

  const submitCard = async (event: FormEvent) => {
    event.preventDefault();
    setCardError(null);
    try {
      await act(() => challenge.start(card));
    } catch (caught) {
      setCardError(errorText(t, caught));
    }
  };
  const startRound = () => act(() => challenge.start()).catch(setStartError);

  return (
    <div className="page page-beat-intro">
      <Hero title={t("public_challenge_title")} sub={t("beat_sub")} mascot="/art/mascot-holding-card.webp"
        ribbon="/art/ribbon-challenge.webp" className="hero-beat" />

      <div className="beat-cards">
        <section className="panel play-card tone-pink" aria-labelledby="play-title">
          <img className="card-deco" src="/art/illustration-fanned-cards.webp" alt="" aria-hidden="true" />
          <div className="card-head">
            <IconBadge icon="cards" tone="pink" size="lg" />
            <div>
              <h2 id="play-title">{t("play_round_title")}</h2>
              <p>{t("play_round_text", { n: size })}</p>
              <div className="round-dots" role="img" aria-label={t("round_dots", { n: size })}>
                {Array.from({ length: size }, (_, i) => <span key={i} className={`dot dot-${i}`} />)}
              </div>
            </div>
          </div>
          {startError ? <ErrorBox error={startError} /> : null}
          <Cta arrow={false} size="lg" className="cta-block" onClick={startRound} disabled={busy}>{t("play_round")}</Cta>
        </section>

        <section className="panel play-card tone-lilac" aria-labelledby="card-title">
          <img className="card-deco card-deco-seven" src="/art/illustration-card-seven.webp" alt="" aria-hidden="true" />
          <div className="card-head">
            <IconBadge icon="pencil" tone="lilac" size="lg" />
            <div>
              <h2 id="card-title">{t("card_title")}</h2>
              <p>{t("card_text")}</p>
            </div>
          </div>
          <form className="card-form" onSubmit={submitCard} noValidate>
            <label htmlFor={inputId}>{t("card_number")}</label>
            <input id={inputId} inputMode="numeric" autoComplete="off" maxLength={3} value={card}
              placeholder={t("card_placeholder")} onChange={(event) => setCard(event.target.value)}
              aria-invalid={cardError ? true : undefined} aria-describedby={cardError ? errorId : undefined} />
            <p id={errorId} className="field-error" aria-live="polite">{cardError}</p>
            <Cta type="submit" arrow={false} size="lg" className="cta-block" disabled={busy}>{t("play_card")}</Cta>
          </form>
        </section>
      </div>

      <WrongCases info={info} />
      <Footer />
    </div>
  );
}

function WrongCases({ info }: { info: ChallengeInfo | null }) {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const [folders, setFolders] = useState<Folder[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (show && !folders) challenge.folders().then(setFolders).catch(setError);
  }, [show, folders]);

  return (
    <section className="panel wrong-panel" aria-labelledby="wrong-title">
      <div className="wrong-main">
        <IconBadge icon="folder" tone="peach" size="lg" />
        <div>
          <h2 id="wrong-title">{t("wrong_title")}</h2>
          <p>{t("wrong_intro")}</p>
          <Toggle checked={show} onChange={setShow} label={t("wrong_show")} />
        </div>
      </div>
      <aside className="wrong-side">
        <p className="note-blue"><Icon name="info" />{t("edu_cases")}</p>
        <p className="small-muted">{t("folders_count")}</p>
        <p className="small-muted">{t("case_credits")}</p>
        {info?.scores && <p className="small-muted">{t("booth_set_note", { ...info.scores })}</p>}
      </aside>
      {show && (
        <div className="folders" aria-live="polite">
          {error ? <ErrorBox error={error} /> : !folders ? <Loading /> : folders.map((folder) => (
            <article key={folder.id} className="folder">
              <h3>
                {t("folder_label", { n: folder.number })} · {t(folder.title_key)}
                {folder.card !== null && <span className="folder-card"> · {t("card_label", { card: folder.card })}</span>}
              </h3>
              <p className="folder-summary">
                {t("wrong_summary", { pred: t(folder.ai_pred), truth: t(folder.truth), percent: folder.percent })}
              </p>
              <ZoomImage src={folder.overlay} alt={t("truth_overlay")} caption={t("truth_overlay")} />
              <p className="small-muted">{t("heatmap_disclaimer")}</p>
              <p>{t(folder.text_key)}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// 2-4 · One case: choose, AI reveal, truth
// ---------------------------------------------------------------------------
function Progress({ round }: { round: Round }) {
  const { t } = useI18n();
  return (
    <div className="progress-block">
      <ol className="stepper" aria-label={t("progress_label")}>
        {round.steps.map((step, i) => (
          <li key={i} className={`step step-${step}`} aria-current={step === "current" ? "step" : undefined}>
            <span className="step-dot">{step === "done" && <Icon name="check" size={14} />}</span>
            <span className="sr-only">{t(`step_${step}`, { n: i + 1 })}</span>
          </li>
        ))}
      </ol>
      <p className="case-label">
        {t("round_progress", { current: round.index + 1, total: round.total, card: round.case!.card })}
      </p>
    </div>
  );
}

interface PlayProps {
  round: Round;
  act: (a: Action) => Promise<void>;
  busy: boolean;
  error: unknown;
  setRound: (round: Round) => void;
}

function Play({ round, act, busy, error }: PlayProps) {
  const { t } = useI18n();
  const phase = round.phase;
  const heroes = {
    choose: { mascot: "/art/mascot-thinking.webp", ribbon: "/art/ribbon-choice.webp" },
    ai: { mascot: "/art/mascot-reveal-thinking.webp", ribbon: "/art/ribbon-reveal.webp" },
    truth: { mascot: "/art/mascot-result-happy-wave.webp", ribbon: "/art/ribbon-result.webp" },
  } as const;
  const art = heroes[phase as keyof typeof heroes];
  const choose = phase === "choose";
  return (
    <div className={`page page-play phase-${phase}`}>
      <Hero title={choose ? t("choice_title") : t("public_challenge_title")}
        sub={choose ? t("public_challenge_title") : undefined}
        mascot={art.mascot} ribbon={art.ribbon} className={`hero-play hero-${phase}`}>
        <Progress round={round} />
      </Hero>
      <section className="panel play-panel" aria-live="polite">
        {phase === "choose" && <Choose round={round} act={act} busy={busy} />}
        {phase === "ai" && <AiReveal round={round} act={act} busy={busy} />}
        {phase === "truth" && <Truth round={round} act={act} busy={busy} />}
        {error ? <ErrorBox error={error} /> : null}
      </section>
      <div className="quit-row">
        <button type="button" className="link-button" onClick={() => act(challenge.end)} disabled={busy}>
          {t("quit_round")}
        </button>
      </div>
      <Footer credits={t("case_credits")} />
    </div>
  );
}

function Choose({ round, act, busy }: { round: Round; act: (a: Action) => Promise<void>; busy: boolean }) {
  const { t } = useI18n();
  const [answer, setAnswer] = useState<ClassName | null>(round.answer);
  const pick = (value: ClassName) => {
    setAnswer(value);
    act(() => challenge.pick(value)).catch(() => setAnswer(round.answer));
  };
  return (
    <div className="split split-choose">
      <div className="image-card">
        <ZoomImage src={round.case!.image} alt={t("original_caption")} caption={`${t("original_caption")} ·`} />
      </div>
      <div className="choice-side">
        <p className="turn-chip"><span className="turn-icon"><Icon name="pencil" size={16} /></span>{t("your_turn")}
          <img className="turn-rays" src="/art/decoration-three-rays.webp" alt="" aria-hidden="true" /></p>
        <h2 className="big-question" id="call-title">{t("whats_your_call")}</h2>
        <p className="lead">{t("choose_before")}</p>
        <p className="muted">{t("okay_to_guess")}</p>
        <fieldset className="choices" aria-labelledby="call-title">
          <legend className="sr-only">{t("answer_group")}</legend>
          {CLASSES.map((value) => (
            <label key={value} className={`choice${answer === value ? " is-selected" : ""}`}>
              <input type="radio" name="answer" value={value} checked={answer === value}
                onChange={() => pick(value)} disabled={busy && answer !== value} />
              <span className="choice-mark" aria-hidden="true">{answer === value && <Icon name="check" size={20} />}</span>
              <span className="choice-text">{t(value)}</span>
            </label>
          ))}
        </fieldset>
        {answer === null && <p className="small-muted" role="note">{t("reveal_locked")}</p>}
        <Cta arrow="plain" size="lg" className="cta-block" disabled={answer === null || busy}
          onClick={() => act(challenge.revealAi)}>{t("reveal_ai")}</Cta>
      </div>
    </div>
  );
}

function AnswerPill({ answer, icon = "pencil" }: { answer: ClassName; icon?: "pencil" | "user" }) {
  const { tn, t } = useI18n();
  return (
    <p className="answer-pill">
      <span className="answer-icon"><Icon name={icon} /></span>
      <span>{tn("your_answer", { answer: <strong>{t(answer)}</strong> })}</span>
    </p>
  );
}

function AiPrediction({ round, compact = false }: { round: Round; compact?: boolean }) {
  const { t, tn } = useI18n();
  const item = round.case!;
  return (
    <div className={`prediction${compact ? " prediction-card" : ""}`}>
      <h2 className="prediction-title">
        {tn("ai_prediction", { prediction: <span className="prediction-value">{t(item.ai_pred!)}</span> })}
      </h2>
      <p className="muted small">{t("confidence_note")}</p>
      {item.ai_correct === false && <p className="error-note">{t("ai_error_note")}</p>}
      <div className="prob-list">
        {CLASSES.map((label) => (
          <ProbabilityBar key={label} label={t("confidence", { label: t(label), percent: item.ai_probs![label] * 100 })}
            value={item.ai_probs![label]} />
        ))}
      </div>
    </div>
  );
}

function AiReveal({ round, act, busy }: { round: Round; act: (a: Action) => Promise<void>; busy: boolean }) {
  const { t } = useI18n();
  return (
    <div className="split split-reveal">
      <div className="image-card">
        <h2 className="image-title"><IconBadge icon="image" tone="pink" size="sm" rays={false} />{t("where_ai_looked")}</h2>
        <ZoomImage src={round.case!.heatmap!} alt={t("heatmap_image")} caption={t("heatmap_caption")} />
        <p className="small-muted">{t("heatmap_disclaimer")}</p>
      </div>
      <div className="reveal-side">
        <AnswerPill answer={round.answer!} />
        <AiPrediction round={round} />
        <div className="compare">
          <img src="/art/mascot-compare-mini.webp" alt="" aria-hidden="true" />
          <p className="bubble">{t("compare_bubble")}</p>
        </div>
        <Cta arrow="plain" size="lg" className="cta-block cta-spread" disabled={busy}
          onClick={() => act(challenge.revealTruth)}>{t("reveal_truth")}</Cta>
      </div>
    </div>
  );
}

function ScoreTile({ who, right, total, icon, tone }:
  { who: string; right: number; total: number; icon: "user" | "robot"; tone: "lilac" | "pink" }) {
  const { t } = useI18n();
  return (
    <div className={`score-tile tone-${tone}`} role="group" aria-label={t("score_aria", { who, right, total })}>
      <IconBadge icon={icon} tone={tone} rays={false} />
      <div aria-hidden="true">
        <span className="score-who">{who}</span>
        <span className="score-value" dir="ltr">{right} / {total}</span>
      </div>
    </div>
  );
}

function Truth({ round, act, busy }: { round: Round; act: (a: Action) => Promise<void>; busy: boolean }) {
  const { t, tn } = useI18n();
  const item = round.case!;
  const last = round.index + 1 >= round.total;
  return (
    <div className="split split-truth">
      <div className="image-card">
        <ZoomImage src={item.overlay!} alt={t("truth_overlay")} caption={t("truth_overlay")} />
        <p className="small-muted">{t("heatmap_disclaimer")}</p>
      </div>
      <div className="truth-side">
        <AnswerPill answer={round.answer!} icon="user" />
        <AiPrediction round={round} compact />
        <div className="label-card" role="status">
          <p className="label-line">
            <IconBadge icon="document" tone="peach" size="sm" rays={false} />
            {tn("dataset_label", { label: <strong>{t(item.truth!)}</strong> })}
          </p>
          <p className="label-headline">{t(item.outcome_key!)}</p>
          <p className="label-text">
            {t(item.explanation_key!, { pred: t(item.ai_pred!), truth: t(item.truth!), percent: item.explanation_percent! })}
          </p>
          {item.overlap_key && <p className="label-text">{t("overlap_question", { answer: t(item.overlap_key) })}</p>}
        </div>
        <div className="score-row">
          <ScoreTile who={t("score_you")} right={round.score.you} total={round.score.played} icon="user" tone="lilac" />
          <ScoreTile who={t("score_ai")} right={round.score.ai} total={round.score.played} icon="robot" tone="pink" />
          <Cta arrow="plain" size="lg" className="cta-next" disabled={busy} onClick={() => act(challenge.next)}>
            {t(last ? "see_score" : "next_case")}
          </Cta>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5 · End of a round
// ---------------------------------------------------------------------------
function End({ round, info, act, busy, error }:
  { round: Round; info: ChallengeInfo | null; act: (a: Action) => Promise<void>; busy: boolean; error: unknown }) {
  const { t } = useI18n();
  const lines = (text: string) => text.split("\n").map((line) => line.replace(/^- /, "")).filter(Boolean);
  return (
    <div className="page page-end">
      <Hero title={t("end_title")} sub={t("score_line", { you: round.score.you, ai: round.score.ai, total: round.score.played })}
        mascot="/art/mascot-result-happy-wave.webp" ribbon="/art/ribbon-result.webp" className="hero-play" />
      <section className="panel end-panel">
        <div className="end-scores">
          <ScoreTile who={t("score_you")} right={round.score.you} total={round.score.played} icon="user" tone="lilac" />
          <ScoreTile who={t("score_ai")} right={round.score.ai} total={round.score.played} icon="robot" tone="pink" />
        </div>
        <p className="station" role="status">{t("station_message")}</p>
        {info?.scores && <p className="small-muted center">{t("booth_set_note", { ...info.scores })}</p>}
        <div className="learn">
          <h2>{t("learn_heading")}</h2>
          <div className="learn-cols">
            <div className="learn-col tone-pink">
              <h3><Icon name="robot" />{t("learn_ai_title")}</h3>
              <ul>{lines(t("learn_ai_points")).map((line) => <li key={line}>{line}</li>)}</ul>
            </div>
            <div className="learn-col tone-lilac">
              <h3><Icon name="user" />{t("learn_doctor_title")}</h3>
              <ul>{lines(t("learn_doctor_points")).map((line) => <li key={line}>{line}</li>)}</ul>
            </div>
          </div>
          <p className="learn-line">{t("learn_line")}</p>
        </div>
        {error ? <ErrorBox error={error} /> : null}
        <Cta size="lg" className="cta-center" disabled={busy} onClick={() => act(challenge.end)}>{t("play_again")}</Cta>
      </section>
      <Footer credits={t("case_credits")} />
    </div>
  );
}
