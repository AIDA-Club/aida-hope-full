import { FormEvent, useCallback, useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { challenge, ChallengeInfo, CLASSES, ClassName, Folder, Round, RoundCase } from "../api";
import { Btn, bullets, Em, ErrorBox, errorText, Loading, Note, Photo, Stamp, Tick, Toggle } from "../components/ui";
import { roundHalfEven } from "../format";
import { useI18n } from "../i18n";

type Action = () => Promise<{ round: Round | null }>;
type Act = (action: Action) => Promise<void>;

const DOT: Record<ClassName, string> = { normal: "var(--green)", benign: "var(--gold)", malignant: "var(--rose)" };
const KEYS: Record<string, ClassName> = { n: "normal", b: "benign", m: "malignant" };

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
  const act = useCallback<Act>(async (action) => {
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

  // The design's keyboard shortcuts: N/B/M choose, R reveals the model, T the truth, Esc leaves.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (busy || !round || target.matches("input, textarea, select") || event.ctrlKey || event.metaKey || event.altKey) return;
      const key = event.key.toLowerCase();
      const run = (action: Action) => { event.preventDefault(); act(action).catch(() => undefined); };
      if (round.phase === "choose" && KEYS[key]) run(() => challenge.pick(KEYS[key]));
      else if (round.phase === "choose" && key === "r" && round.answer) run(challenge.revealAi);
      else if (round.phase === "ai" && key === "t") run(challenge.revealTruth);
      else if (event.key === "Escape") run(challenge.end);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [round, busy, act]);

  if (round === undefined) {
    return <section className="screen">{error ? <ErrorBox error={error} onRetry={load} /> : <Loading />}</section>;
  }
  return (
    <section className="screen" id="beat">
      {round === null && <Waiting info={info} act={act} busy={busy} />}
      {round?.phase === "choose" && <Choose round={round} act={act} busy={busy} />}
      {round?.phase === "ai" && <ModelCall round={round} act={act} busy={busy} />}
      {round?.phase === "truth" && <Truth round={round} act={act} busy={busy} />}
      {round?.phase === "end" && <End round={round} info={info} act={act} busy={busy} />}
      {error && round !== null ? <ErrorBox error={error} /> : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Waiting: how it works, a card number, or a random round
// ---------------------------------------------------------------------------
function Waiting({ info, act, busy }: { info: ChallengeInfo | null; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const [card, setCard] = useState("");
  const [cardError, setCardError] = useState<string | null>(null);
  const [startError, setStartError] = useState<unknown>(null);
  const inputId = useId();
  const errorId = useId();
  const size = info?.round_size ?? 5;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setCardError(null);
    try {
      await act(() => challenge.start(card));
    } catch (caught) {
      setCardError(errorText(t, caught));
    }
  };

  return (
    <>
      <div className="round waiting">
        <div className="text stack-gap">
          <div className="tagline"><span className="tag">{t("tag")}</span>
            <span className="eyebrow">{t("beat_eyebrow", { n: info?.n_cards ?? 30 })}</span></div>
          <h1 className="h1-beat">{t("beat_h1_a")} <Em>{t("beat_h1_em")}</Em></h1>
          <p>{t("beat_intro")}</p>
          <ol className="steps">
            {[1, 2, 3].map((n) => (
              <li className="step" key={n}><span className="n" aria-hidden="true">{n}</span>
                <h3>{t(`beat_step${n}`)}</h3><p className="small">{t(`beat_step${n}_text`)}</p></li>
            ))}
          </ol>
          <Note>{t("beat_note")}</Note>
        </div>
        <div className="waiting-side">
          <img className="mascot point" src="/pinkai/m-photo-point.webp" alt={t("mascot_point_alt")} />
          <form className="card staff" onSubmit={submit} noValidate>
            <div className="tape-bit" aria-hidden="true" />
            <div className="staff-head"><span className="badge">{t("card_badge")}</span><span className="small">{t("card_hint")}</span></div>
            <div className="row">
              <label className="sr-only" htmlFor={inputId}>{t("card_number")}</label>
              <input id={inputId} inputMode="numeric" autoComplete="off" maxLength={3} value={card}
                placeholder={t("card_placeholder")} onChange={(event) => setCard(event.target.value)}
                aria-invalid={cardError ? true : undefined} aria-describedby={cardError ? errorId : undefined} />
              <Btn type="submit" disabled={busy}>{t("card_show")}</Btn>
            </div>
            <p id={errorId} className="field-error" aria-live="polite">{cardError}</p>
            <Btn variant="ghost" disabled={busy}
              onClick={() => act(() => challenge.start()).catch(setStartError)}>{t("or_round", { n: size })}</Btn>
            {startError ? <ErrorBox error={startError} /> : null}
            <div className="keys" aria-hidden="true">
              <div><kbd>N</kbd> <kbd>B</kbd> <kbd>M</kbd> {t("keys_choose")}</div><div><kbd>R</kbd> {t("keys_reveal_ai")}</div>
              <div><kbd>T</kbd> {t("keys_reveal_truth")}</div><div><kbd>Esc</kbd> {t("keys_leave")}</div>
            </div>
          </form>
        </div>
      </div>
      <WrongCases info={info} />
    </>
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
    <section className="col wrong" aria-labelledby="wrong-title">
      <h2 id="wrong-title">{t("wrong_title")}</h2>
      <p>{t("wrong_intro")}</p>
      {info?.scores && <p className="small">{t("booth_set_note", { ...info.scores })}</p>}
      <Toggle checked={show} onChange={setShow} label={t("wrong_show")} />
      {show && (
        <div className="folders" aria-live="polite">
          {error ? <ErrorBox error={error} /> : !folders ? <Loading /> : folders.map((folder, index) => (
            <article key={folder.id} className="folder">
              <Photo src={folder.overlay} alt={t("truth_overlay")} tilt={index % 2 ? "r" : "l"}
                caption={`${t("folder_label", { n: folder.number })} · ${t(folder.title_key)}`} />
              <p className="folder-summary">
                {t("wrong_summary", { pred: t(folder.ai_pred), truth: t(folder.truth), percent: folder.percent })}
                {folder.card !== null && <span className="small"> · {t("card_label", { card: folder.card })}</span>}
              </p>
              <p className="small">{t(folder.text_key)}</p>
            </article>
          ))}
          {folders && <Note>{t("folders_note")} {t("heatmap_disclaimer")}</Note>}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// The round: rail, your call, the model's call, the truth
// ---------------------------------------------------------------------------
function Rail({ round, step }: { round: Round; step: 1 | 2 | 3 }) {
  const { t } = useI18n();
  return (
    <div className="rail">
      <span className="case">{t("rail_case", { card: round.case!.card })}</span>
      {round.total > 1 && <span className="round-count">{t("rail_round", { current: round.index + 1, total: round.total })}</span>}
      <ol className="rail-steps" aria-label={t("rail_label")}>
        {[1, 2, 3].map((n) => (
          <li key={n} className={`s${n === step ? " on" : ""}${n < step ? " done" : ""}`} aria-current={n === step ? "step" : undefined}>
            {n > 1 && <span className="dots" aria-hidden="true" />}<i>{n}</i>{t(`rail_${n}`)}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Choose({ round, act, busy }: { round: Round; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const [answer, setAnswer] = useState<ClassName | null>(round.answer);
  useEffect(() => setAnswer(round.answer), [round.answer]);
  const item = round.case!;
  const pick = (value: ClassName) => {
    setAnswer(value);
    act(() => challenge.pick(value)).catch(() => setAnswer(round.answer));
  };
  return (
    <div className="phase">
      <Rail round={round} step={1} />
      <div className="round">
        <div className="photo-wrap">
          <Photo src={item.image} alt={t("original_image")} tilt="l" caption={t("photo_look", { card: item.card })} />
          <img className="mascot magnify" src="/pinkai/m-magnify.webp" alt="" aria-hidden="true" />
        </div>
        <div className="stack-gap">
          <span className="eyebrow">{t("step_of", { n: 1 })}</span>
          <h1 className="h1-step">{t("choose_h1_a")} <Em>{t("choose_h1_em")}</Em></h1>
          <p>{t("choose_p")}</p>
          <div className="choices" role="radiogroup" aria-label={t("choose_group")}>
            {CLASSES.map((value) => (
              <button key={value} type="button" role="radio" aria-checked={answer === value}
                className="choice" disabled={busy && answer !== value} onClick={() => pick(value)}>
                <i style={{ background: DOT[value] }} aria-hidden="true" />{t(value)}
                <small>{t(`choice_${value}`)}</small><kbd aria-hidden="true">{value[0].toUpperCase()}</kbd>
              </button>
            ))}
          </div>
          {answer === null && <p className="small" role="note">{t("reveal_locked")}</p>}
          <Btn className="wide" disabled={answer === null || busy} onClick={() => act(challenge.revealAi)}>
            {t("reveal_model")} <kbd>R</kbd>
          </Btn>
          <Note>{t("choose_note")}</Note>
          <Btn variant="link" onClick={() => act(challenge.end)}>{t("leave_round")}</Btn>
        </div>
      </div>
    </div>
  );
}

const pct = (value: number) => roundHalfEven(value * 100, 0);

function Probabilities({ item }: { item: RoundCase }) {
  const { t } = useI18n();
  return (
    <div className="bars" role="group" aria-label={t("probabilities")}>
      {CLASSES.map((label) => (
        <div className="b" key={label}>
          <span>{t(label)}</span>
          <i role="progressbar" aria-label={t(label)} aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={Math.round(item.ai_probs![label] * 100)}
            style={{ "--w": `${Math.max(item.ai_probs![label] * 100, 1)}%`, "--c": DOT[label] } as React.CSSProperties} />
          <b dir="ltr">{pct(item.ai_probs![label])}%</b>
        </div>
      ))}
    </div>
  );
}

function ModelCall({ round, act, busy }: { round: Round; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const item = round.case!;
  return (
    <div className="phase">
      <Rail round={round} step={2} />
      <div className="round">
        <div className="stack-gap">
          <Photo src={item.heatmap!} alt={t("heatmap_image")} tilt="r" caption={t("photo_heat")} />
          <Note>{t("heatmap_disclaimer")}</Note>
        </div>
        <div className="stack-gap">
          <span className="eyebrow">{t("step_of", { n: 2 })}</span>
          <h1 className="h1-step">{t("ai_h1_a")} <Em>{t(item.ai_pred!)}.</Em></h1>
          <div className="ledger">
            <div className="row"><span>{t("ledger_your_call")}</span><b>{t(round.answer!)}</b><Tick ok={null} /></div>
            <div className="row"><span>{t("ledger_model")}</span>
              <b>{t(item.ai_pred!)} <span className="small">{t("ledger_sure", { percent: pct(item.ai_probs![item.ai_pred!]) })}</span></b><Tick ok={null} /></div>
          </div>
          <div className="card">
            <span className="eyebrow">{t("probabilities")}</span>
            <Probabilities item={item} />
            <p className="small">{t("confidence_note")}</p>
            {item.ai_correct === false && <p className="error-note">{t("ai_error_note")}</p>}
          </div>
          <Btn className="wide" disabled={busy} onClick={() => act(challenge.revealTruth)}>{t("reveal_truth")} <kbd>T</kbd></Btn>
          <Btn variant="link" onClick={() => act(challenge.end)}>{t("leave_round")}</Btn>
        </div>
      </div>
    </div>
  );
}

function stampFor(item: RoundCase, t: (key: string) => string) {
  if (item.ai_correct) return null;
  const key = item.truth === "malignant" ? "stamp_missed" : item.ai_pred === "malignant" ? "stamp_false_alarm" : "stamp_wrong";
  return <Stamp className="on-heat">{t(key)}</Stamp>;
}

function Lessons() {
  const { t } = useI18n();
  return (
    <div className="pair">
      <div><div className="eyebrow">{t("learn_ai_title")}</div><ul>{bullets(t("learn_ai_points")).map((l) => <li key={l}>{l}</li>)}</ul></div>
      <div><div className="eyebrow">{t("learn_doctor_title")}</div><ul>{bullets(t("learn_doctor_points")).map((l) => <li key={l}>{l}</li>)}</ul></div>
    </div>
  );
}

function ScoreLedger({ round }: { round: Round }) {
  const { t } = useI18n();
  const { you, ai, played } = round.score;
  return (
    <div className="ledger score" role="status" aria-label={t("score_so_far")}>
      <div className="row"><span>{t("score_you")}</span><b dir="ltr">{t("score_of", { right: you, total: played })}</b></div>
      <div className="row"><span>{t("score_ai")}</span><b dir="ltr">{t("score_of", { right: ai, total: played })}</b></div>
    </div>
  );
}

function Truth({ round, act, busy }: { round: Round; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const item = round.case!;
  const last = round.index + 1 >= round.total;
  const explanation = t(item.explanation_key!, { pred: t(item.ai_pred!), truth: t(item.truth!), percent: item.explanation_percent! });
  return (
    <div className="phase">
      <Rail round={round} step={3} />
      <div className="round">
        <div className="stack-gap">
          <h1 className="h1-step">{t("truth_h1_a")} <Em>{t(item.truth!).toLocaleLowerCase()}.</Em></h1>
          <div className="three">
            <Photo src={item.image} alt={t("original_image")} tilt="l" caption={t("photo_saw")} />
            <Photo src={item.heatmap!} alt={t("heatmap_image")} tilt="r" tape={false} caption={t("photo_heat")} stamp={stampFor(item, t)} />
            <Photo src={item.overlay!} alt={t("truth_overlay")} tilt="l" caption={t("photo_outline")} />
          </div>
          <Note>{explanation}</Note>
          <p className="small">{t("truth_overlay")} · {t("heatmap_disclaimer")}</p>
          <div className="quote">“{t("learn_line")}”</div>
        </div>
        <div className="stack-gap">
          <div className="ledger">
            <div className="row"><span>{t("ledger_your_call")}</span><b>{t(round.answer!)}</b><Tick ok={round.answer === item.truth} /></div>
            <div className="row"><span>{t("ledger_model")}</span>
              <b>{t(item.ai_pred!)} <span className="small">{t("ledger_sure", { percent: pct(item.ai_probs![item.ai_pred!]) })}</span></b>
              <Tick ok={item.ai_correct!} /></div>
            <div className="row"><span>{t("ledger_truth")}</span><b>{t(item.truth!)}</b><Tick ok={null} /></div>
          </div>
          <h2>{t("teaches")}</h2>
          <p><span className="hl">{t(item.outcome_key!)}</span></p>
          {item.overlap_key && <p className="small">{t("overlap_question", { answer: t(item.overlap_key) })}</p>}
          <Lessons />
          <ScoreLedger round={round} />
          <div className="next-row">
            <Btn disabled={busy} onClick={() => act(challenge.next)}>{t(last ? "see_score" : "next_case")}</Btn>
            <Link className="hand worried" to="/ask?topic=get_help">{t("worried")}</Link>
            <img className="mascot photo-mascot" src="/pinkai/m-photo.webp" alt="" aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
  );
}

function End({ round, info, act, busy }: { round: Round; info: ChallengeInfo | null; act: Act; busy: boolean }) {
  const { t } = useI18n();
  return (
    <div className="round">
      <div className="stack-gap">
        <div className="tagline"><span className="tag">{t("tag")}</span><span className="eyebrow">{t("end_title")}</span></div>
        <h1 className="h1-step">{t("end_h1_a")} <Em>{t("end_h1_em")}</Em></h1>
        <ScoreLedger round={round} />
        <div className="quote">{t("station_message")}</div>
        {info?.scores && <p className="small">{t("booth_set_note", { ...info.scores })}</p>}
        <div className="next-row">
          <Btn disabled={busy} onClick={() => act(challenge.end)}>{t("play_again")}</Btn>
        </div>
      </div>
      <div className="stack-gap">
        <h2>{t("learn_heading")}</h2>
        <Lessons />
        <p><span className="hl">{t("learn_line")}</span></p>
        <img className="mascot end-mascot" src="/pinkai/m-clipboard.webp" alt="" aria-hidden="true" />
      </div>
    </div>
  );
}
