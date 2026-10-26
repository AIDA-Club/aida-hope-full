import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { About, aboutApi, challenge, ChallengeInfo, CLASSES, ClassName, Folder, Round, RoundCase } from "../api";
import { Btn, bullets, CountUp, Em, ErrorBox, errorText, Loading, Note, pct, Photo, sparkle, Stamp, Tick, Toggle } from "../components/ui";
import { I18n, useI18n } from "../i18n";

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

  // Keyboard shortcuts: N/B/M choose, R reveals the model, T the truth, Esc leaves the round.
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
      {round?.phase === "choose" && <Choose key={`c${round.index}`} round={round} act={act} busy={busy} />}
      {round?.phase === "ai" && <ModelCall round={round} act={act} busy={busy} />}
      {round?.phase === "truth" && <Truth round={round} act={act} busy={busy} />}
      {round?.phase === "end" && <End round={round} info={info} act={act} busy={busy} />}
      {error && round !== null ? <ErrorBox error={error} /> : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Waiting: how it works, the hidden next case, a card number, the clues
// ---------------------------------------------------------------------------
function Clues() {
  const { t } = useI18n();
  const scan = <><rect width="64" height="44" rx="4" fill="#4B4F54" /><path d="M0 9c20-4 40 5 64-1M0 36c22 3 42-4 64 1" stroke="#6E737A" strokeWidth="2" fill="none" /></>;
  const clues: Array<[string, ReactNode, ReactNode]> = [
    ["shape", <>{scan}<ellipse cx="32" cy="22" rx="15" ry="10" fill="#17191C" /></>,
      <>{scan}<path d="M17 25l5-11 8 3 6-7 8 8 4 9-9 4-5 4-8-5z" fill="#17191C" /></>],
    ["edges", <>{scan}<ellipse cx="32" cy="22" rx="14" ry="10" fill="#17191C" stroke="#9AA0A6" strokeWidth="1.2" /></>,
      <>{scan}<path d="M32 22V5M32 22l17-10M32 22l21 4M32 22l13 15M32 22l-12 16M32 22l-20 4M32 22L15 9" stroke="#17191C" strokeWidth="2" strokeLinecap="round" /><ellipse cx="32" cy="22" rx="11" ry="8" fill="#17191C" /></>],
    ["direction", <><rect width="64" height="44" rx="4" fill="#4B4F54" /><path d="M4 5h56" stroke="#9AA0A6" strokeWidth="2" strokeLinecap="round" /><ellipse cx="32" cy="25" rx="18" ry="8" fill="#17191C" /></>,
      <><rect width="64" height="44" rx="4" fill="#4B4F54" /><path d="M4 5h56" stroke="#9AA0A6" strokeWidth="2" strokeLinecap="round" /><ellipse cx="32" cy="25" rx="9" ry="14" fill="#17191C" /></>],
    ["behind", <><rect width="64" height="44" rx="4" fill="#4B4F54" /><path d="M19 18h26v26H19z" fill="#A3A8AE" opacity=".55" /><ellipse cx="32" cy="15" rx="13" ry="9" fill="#17191C" /></>,
      <><rect width="64" height="44" rx="4" fill="#4B4F54" /><path d="M19 18h26v26H19z" fill="#17191C" opacity=".7" /><ellipse cx="32" cy="15" rx="13" ry="9" fill="#17191C" /></>],
  ];
  return (
    <div className="card clues-card">
      <div className="tape-bit" aria-hidden="true" />
      <div className="answer-head"><h3>{t("clues_title")}</h3><span className="hand">{t("clues_sub")}</span></div>
      <div className="clues">
        {clues.map(([key, ok, bad]) => (
          <div className="clue" key={key}>
            <b>{t(`clue_${key}`)}</b>
            <div className="sketches">
              <figure><svg viewBox="0 0 64 44" aria-hidden="true">{ok}</svg><figcaption>{t(`clue_${key}_ok`)}</figcaption></figure>
              <figure className="warn"><svg viewBox="0 0 64 44" aria-hidden="true">{bad}</svg><figcaption>{t(`clue_${key}_bad`)}</figcaption></figure>
            </div>
          </div>
        ))}
      </div>
      <div className="clue-key"><span><i className="ok" />{t("clue_key_ok")}</span><span><i className="bad" />{t("clue_key_bad")}</span></div>
    </div>
  );
}

function Waiting({ info, act, busy }: { info: ChallengeInfo | null; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const [card, setCard] = useState("");
  const [cardError, setCardError] = useState<string | null>(null);
  const [startError, setStartError] = useState<unknown>(null);
  const [about, setAbout] = useState<About | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const size = info?.round_size ?? 5;
  const cards = info?.n_cards ?? 30;
  useEffect(() => { aboutApi.get().then(setAbout).catch(() => setAbout(null)); }, []);

  const open = async (number: string) => {
    setCardError(null);
    try {
      await act(() => challenge.start(number));
    } catch (caught) {
      setCardError(errorText(t, caught));
      const el = input.current;
      if (el) { el.classList.remove("nope"); void el.offsetWidth; el.classList.add("nope"); }
    }
  };
  const submit = (event: FormEvent) => { event.preventDefault(); open(card); };

  return (
    <>
      <div className="round waiting" data-phase="waiting">
        <div className="text stack-gap">
          <div className="tagline beat-tagline"><span className="tag">{t("tag")}</span>
            <span className="eyebrow">{t("beat_eyebrow", { n: cards })}</span></div>
          <h1 className="h1-beat">{t("beat_h1_a")} <Em>{t("beat_h1_em")}</Em></h1>
          <p>{t("beat_intro")}</p>
          <ol className="steps beat-steps">
            {[1, 2, 3].map((n) => (
              <li className="step" key={n}><span className="n" aria-hidden="true">{n}</span>
                <h3>{t(`beat_step${n}`)}</h3><p className="small">{t(`beat_step${n}_text`)}</p></li>
            ))}
          </ol>
          <Note className="beat-note">{t("beat_note")}</Note>
        </div>

        <div className="waiting-side">
          <div className="deck" role="img" aria-label={t("deck_label")}>
            <div className="photo back"><img src="/api/cards/04/original" alt="" /></div>
            <div className="photo front">
              <div className="tape-bit" />
              <div className="frost"><img src="/api/cards/17/original" alt="" /><span className="q" aria-hidden="true">?</span></div>
              <div className="cap">{t("deck_cap")}</div>
              <span className="stamp">{t("deck_stamp")}</span>
            </div>
            <img className="mascot" src="/pinkai/m-photo-point.webp" alt="" />
          </div>
          <form className="card staff" onSubmit={submit} noValidate>
            <div className="tape-bit" aria-hidden="true" />
            <div className="staff-head"><span className="badge">{t("card_badge")}</span><span className="small">{t("card_hint")}</span></div>
            <div className="row">
              <label className="sr-only" htmlFor="case-number">{t("card_number")}</label>
              <input id="case-number" ref={input} inputMode="numeric" autoComplete="off" maxLength={3} value={card}
                placeholder={t("card_placeholder")} onChange={(event) => setCard(event.target.value)}
                aria-invalid={cardError ? true : undefined} aria-describedby="case-hint"
                onAnimationEnd={(event) => event.currentTarget.classList.remove("nope")} />
              <Btn type="submit" disabled={busy}>{t("card_show")}</Btn>
            </div>
            <div className="case-hint" id="case-hint">
              <span aria-live="polite">{cardError ?? t("case_hint")}</span>
              <Btn variant="link" disabled={busy} onClick={() => open(String(1 + Math.floor(Math.random() * cards)))}>{t("random_case")}</Btn>
            </div>
            <Btn variant="ghost" disabled={busy}
              onClick={() => act(() => challenge.start()).catch(setStartError)}>{t("or_round", { n: size })}</Btn>
            {startError ? <ErrorBox error={startError} /> : null}
            <div className="keys" aria-hidden="true">
              <div><kbd>N</kbd> <kbd>B</kbd> <kbd>M</kbd> {t("keys_choose")}</div><div><kbd>R</kbd> {t("keys_reveal_ai")}</div>
              <div><kbd>T</kbd> {t("keys_reveal_truth")}</div><div><kbd>Esc</kbd> {t("keys_leave")}</div>
            </div>
          </form>
          {about && (
            <div className="vs" role="group" aria-label={t("vs_label", { caught: about.caught, total: about.malignant_total })}>
              <div className="side ai" aria-hidden="true"><span className="eyebrow">{t("vs_ai")}</span>
                <b dir="ltr"><CountUp to={about.caught} /><small>/{about.malignant_total}</small></b>
                <span className="small">{t("vs_ai_small")}</span></div>
              <span className="versus" aria-hidden="true">vs</span>
              <div className="side you" aria-hidden="true"><span className="eyebrow">{t("vs_you")}</span><b>?</b>
                <span className="small">{t("vs_you_small")}</span></div>
            </div>
          )}
        </div>

        <div className="waiting-more"><Clues /></div>
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
// The round: your call, the model's call, the truth, the end
// ---------------------------------------------------------------------------
/** The card number (and the case count in a set), pinned to the corner of the photo. */
function CardPin({ round }: { round: Round }) {
  const { t } = useI18n();
  return (
    <div className="rail card-pin">
      <span className="case">{t("rail_case", { card: round.case!.card })}</span>
      {round.total > 1 && <span className="round-count">{t("rail_round", { current: round.index + 1, total: round.total })}</span>}
    </div>
  );
}

/** "Step 1 of 3: Your call" */
function StepLabel({ step }: { step: 1 | 2 | 3 }) {
  const { t } = useI18n();
  return <span className="eyebrow step-label">{t("step_named", { n: step, step: t(`rail_${step}`) })}</span>;
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
    <div className="phase" data-phase="choose">
      <div className="round">
        <div className="photo-wrap">
          <Photo src={item.image} alt={t("original_image")} tilt="l" caption={t("photo_look", { card: item.card })} />
          <img className="mascot magnify" src="/pinkai/m-magnify.webp" alt="" aria-hidden="true" />
          <CardPin round={round} />
        </div>
        <div className="stack-gap">
          <StepLabel step={1} />
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

/** The model's three probabilities, its own call highlighted (the design's probs row). */
function ProbsRow({ item }: { item: RoundCase }) {
  const { t } = useI18n();
  return (
    <div className="row probs-row">
      <span>{t("probs_row")}</span>
      <div className="probs">
        {CLASSES.map((label) => (
          <div key={label} className={`pb${label === item.ai_pred ? " on" : ""}`}>
            <em>{t(label)}</em>
            <i role="progressbar" aria-label={t(label)} aria-valuemin={0} aria-valuemax={100}
              aria-valuenow={Math.round(item.ai_probs![label] * 100)}
              style={{ "--w": `${(item.ai_probs![label] * 100).toFixed(1)}%` } as React.CSSProperties} />
            <b dir="ltr">{pct(item.ai_probs![label])}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelCall({ round, act, busy }: { round: Round; act: Act; busy: boolean }) {
  const { t } = useI18n();
  const item = round.case!;
  return (
    <div className="phase" data-phase="ai">
      <div className="round">
        <div className="stack-gap">
          <div className="photo-wrap">
            <Photo src={item.heatmap!} alt={t("heatmap_image")} tilt="r" caption={t("photo_heat")} />
            <CardPin round={round} />
          </div>
          <Note>{t("heatmap_disclaimer")}</Note>
        </div>
        <div className="stack-gap">
          <StepLabel step={2} />
          <h1 className="h1-step">{t("ai_h1_a")} <Em>{t(item.ai_pred!)}.</Em></h1>
          <div className="ledger">
            <div className="row"><span>{t("ledger_your_call")}</span><b>{t(round.answer!)}</b><Tick ok={null} /></div>
            <div className="row"><span>{t("ledger_model")}</span>
              <b>{t(item.ai_pred!)} <span className="small">{t("ledger_sure", { percent: pct(item.ai_probs![item.ai_pred!]).replace("%", "") })}</span></b>
              <Tick ok={null} /></div>
            <ProbsRow item={item} />
          </div>
          <p className="small">{t("confidence_note")}</p>
          {item.ai_correct === false && <p className="error-note">{t("ai_error_note")}</p>}
          <Btn className="wide" disabled={busy} onClick={() => act(challenge.revealTruth)}>{t("reveal_truth")} <kbd>T</kbd></Btn>
          <Btn variant="link" onClick={() => act(challenge.end)}>{t("leave_round")}</Btn>
        </div>
      </div>
    </div>
  );
}

/** What this case teaches: the design's case-by-case lesson, from the API's own verdicts. */
function lesson(item: RoundCase, t: I18n["t"], tn: I18n["tn"]): { text: ReactNode; quote: string } {
  const probs = item.ai_probs!;
  const ai = item.ai_pred!;
  const truth = item.truth!;
  const sure = probs[ai];
  const percent = pct(sure);
  const hl = (text: string) => <span className="hl">{text}</span>;
  if (!item.ai_correct) {
    if (truth === "malignant") {
      const confident = sure >= 0.8;
      return {
        text: tn("lesson_fn", {
          hl: hl(confident ? t("lesson_fn_confident") : t("lesson_fn_unsure", { percent })),
          looked: item.explanation_key?.endsWith("_on_target") ? t("lesson_fn_looked") : "",
        }, { pred: t(ai).toLocaleLowerCase() }),
        quote: t(confident ? "quote_confident" : "quote_unsure"),
      };
    }
    if (ai === "malignant") return { text: tn("lesson_fp", { hl: hl(t("lesson_fp_hl", { percent })) }), quote: t("quote_false_alarm") };
    const call = hl(t("lesson_call_hl", { pred: t(ai).toLocaleLowerCase(), percent }));
    return truth === "normal"
      ? { text: tn("lesson_no_lump", { hl: call }), quote: t("quote_pattern") }
      : { text: tn("lesson_missed_benign", { hl: call }), quote: t("quote_unsure") };
  }
  const what = t(`what_${truth}`);
  const runner = CLASSES.filter((label) => label !== ai).sort((a, b) => probs[b] - probs[a])[0];
  if (sure < 0.6) {
    return {
      text: tn("lesson_just", { hl: hl(t("lesson_just_hl", { percent })) },
        { what, runner: t(runner).toLocaleLowerCase(), runner_percent: pct(probs[runner]) }),
      quote: t("quote_just"),
    };
  }
  if (truth !== "normal" && item.overlap_key === "overlap_no") {
    return { text: tn("lesson_reason", { hl: hl(t("lesson_reason_hl")) }, { what, percent }), quote: t("quote_reason") };
  }
  return {
    text: tn("lesson_right", { hl: hl(t("lesson_right_hl", { percent })) }, {
      what,
      attention: item.overlap_key === "overlap_yes" ? t("lesson_attention") : "",
      tail: t(truth === "malignant" ? "lesson_tail_cancer" : "lesson_tail_calm"),
    }),
    quote: t("quote_good"),
  };
}

function stampFor(item: RoundCase, t: I18n["t"]) {
  if (item.ai_correct) return <Stamp className="on-heat ok">{t("stamp_right")}</Stamp>;
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
  const { t, tn } = useI18n();
  const item = round.case!;
  const last = round.index + 1 >= round.total;
  const right = round.answer === item.truth;
  const explanation = t(item.explanation_key!, { pred: t(item.ai_pred!), truth: t(item.truth!), percent: item.explanation_percent! });
  const { text, quote } = lesson(item, t, tn);
  const strip = useRef<HTMLDivElement>(null);
  const yourRow = useRef<HTMLDivElement>(null);
  const [photo, setPhoto] = useState(0);

  useEffect(() => {
    if (!right) return;
    const timer = window.setTimeout(() => sparkle(yourRow.current), 1000);
    return () => window.clearTimeout(timer);
  }, [right]);

  // On a phone the three photos are a sideways strip; the pager scrolls it and follows it.
  const goTo = (index: number) => {
    const container = strip.current;
    const target = container?.children[index] as HTMLElement | undefined;
    if (!container || !target) return;
    container.scrollTo({ left: target.offsetLeft - (container.clientWidth - target.offsetWidth) / 2, behavior: "smooth" });
    setPhoto(index);
  };
  const onScroll = () => {
    const container = strip.current;
    if (!container) return;
    const middle = container.scrollLeft + container.clientWidth / 2;
    const photos = Array.from(container.children) as HTMLElement[];
    const distance = (p: HTMLElement) => Math.abs(p.offsetLeft + p.offsetWidth / 2 - middle);
    setPhoto(photos.indexOf(photos.reduce((a, b) => (distance(b) < distance(a) ? b : a))));
  };

  return (
    <div className="phase" data-phase="truth">
      <div className="round">
        <div className="t-left stack-gap">
          <StepLabel step={3} />
          <h1 className="h1-step">{t("truth_h1_a")} <Em>{t(item.truth!).toLocaleLowerCase()}.</Em></h1>
          <div className="photo-wrap three-wrap">
            <CardPin round={round} />
            <div className="three" ref={strip} onScroll={onScroll}>
              <Photo src={item.image} alt={t("original_image")} tilt="l" caption={t("photo_saw")} />
              <Photo src={item.heatmap!} alt={t("heatmap_image")} tilt="r" tape={false} caption={t("photo_heat")} stamp={stampFor(item, t)} />
              <Photo src={item.overlay!} alt={t("truth_overlay")} tilt="l"
                caption={item.truth === "normal" ? t("nothing_to_outline") : t("photo_outline")} />
            </div>
          </div>
          <div className="pager" role="group" aria-label={t("pager_label")}>
            {["pager_saw", "pager_heat", "pager_outline"].map((key, index) => (
              <button key={key} type="button" aria-pressed={photo === index} onClick={() => goTo(index)}>{t(key)}</button>
            ))}
          </div>
          <Note>{explanation}</Note>
          <p className="small caveat">{t("truth_overlay")} · {t("heatmap_disclaimer")}</p>
          <div className="quote">“{quote}”</div>
        </div>
        <div className="t-right stack-gap">
          <div className="ledger">
            <div className={`row ${right ? "right" : "wrong"}`} ref={yourRow}>
              <span>{t("ledger_your_call")}</span><b>{t(round.answer!)}</b><Tick ok={right} /></div>
            <div className="row"><span>{t("ledger_model")}</span>
              <b>{t(item.ai_pred!)} <span className="small">{t("ledger_sure", { percent: pct(item.ai_probs![item.ai_pred!]).replace("%", "") })}</span></b>
              <Tick ok={item.ai_correct!} /></div>
            <ProbsRow item={item} />
            <div className="row"><span>{t("ledger_truth")}</span><b>{t(item.truth!)}</b><Tick ok={null} /></div>
          </div>
          <h2>{t("teaches")}</h2>
          <p className="outcome"><b>{t(item.outcome_key!)}</b></p>
          <p id="t-lesson">{text}</p>
          {item.overlap_key && <p className="small overlap">{t("overlap_question", { answer: t(item.overlap_key) })}</p>}
          <Lessons />
          <ScoreLedger round={round} />
          <div className="next-row">
            <Btn disabled={busy} onClick={() => act(challenge.next)}>{t(last ? "see_score" : "next_case")}</Btn>
            <Link className="hand" to="/ask?topic=get_help">{t("worried")}</Link>
            <img className="mascot" src="/pinkai/m-photo.webp" alt="" aria-hidden="true" />
          </div>
        </div>
      </div>
    </div>
  );
}

function End({ round, info, act, busy }: { round: Round; info: ChallengeInfo | null; act: Act; busy: boolean }) {
  const { t } = useI18n();
  return (
    <div className="round" data-phase="end">
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
