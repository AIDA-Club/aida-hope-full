import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { askAida, ChatState } from "../api";
import { Btn, Em, ErrorBox, errorText, Loading } from "../components/ui";
import { useI18n } from "../i18n";

const TOPICS = ["know_signs", "myth_fact", "explain_term", "get_help"] as const;

function TopicIcon({ topic }: { topic: string }) {
  const paths: Record<string, JSX.Element> = {
    know_signs: <><path d="M3 14s4-7 11-7 11 7 11 7-4 7-11 7S3 14 3 14z" fill="none" stroke="#C63D76" strokeWidth="2.2" /><circle cx="14" cy="14" r="3.5" fill="none" stroke="#C63D76" strokeWidth="2.2" /></>,
    myth_fact: <><circle cx="14" cy="14" r="11" fill="none" stroke="#7A1F46" strokeWidth="2.2" /><path d="M10.5 11a3.5 3.5 0 1 1 5 3.2c-1 .5-1.5 1.2-1.5 2.3M14 20.5v.5" fill="none" stroke="#7A1F46" strokeWidth="2.2" strokeLinecap="round" /></>,
    explain_term: <><path d="M5 5h14l4 4v14H5z" fill="none" stroke="#C63D76" strokeWidth="2.2" strokeLinejoin="round" /><path d="M9 12h10M9 16h10M9 20h6" stroke="#C63D76" strokeWidth="2.2" strokeLinecap="round" /></>,
    get_help: <path d="M14 25s-9-6.5-9-13a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6.5-9 13-9 13z" fill="none" stroke="#C63D76" strokeWidth="2.2" strokeLinejoin="round" />,
  };
  return <svg viewBox="0 0 28 28" aria-hidden="true">{paths[topic]}</svg>;
}

export default function Ask() {
  const { t, lang } = useI18n();
  const [params, setParams] = useSearchParams();
  const [state, setState] = useState<ChatState | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const errorId = useId();

  const run = async (work: () => Promise<ChatState>, question?: string) => {
    setBusy(true);
    setInputError(null);
    if (question) setPending(question);
    try {
      setState(await work());
      if (question) setMessage("");
    } catch (caught) {
      setInputError(errorText(t, caught));
    } finally {
      setPending(null);
      setBusy(false);
    }
  };
  const card = useRef<HTMLDivElement>(null);
  const openTopic = async (topic: string) => {
    setActiveTopic(topic);
    await run(() => askAida.topic(topic, lang));
    const element = card.current;
    if (!element) return;
    // the design: a new answer slides in, and on a phone the card is brought into view
    element.classList.remove("swap");
    void element.offsetWidth;
    element.classList.add("swap");
    if (window.matchMedia("(max-width: 1099px)").matches) {
      const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      element.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
    }
  };

  const load = () => {
    setLoadError(null);
    askAida.state().then(setState).catch(setLoadError);
  };
  useEffect(load, []);
  // ?topic=get_help (from "Where to get help" links) opens that answer once.
  useEffect(() => {
    const topic = params.get("topic");
    if (state && topic && (TOPICS as readonly string[]).includes(topic)) {
      setParams((current) => { current.delete("topic"); return current; }, { replace: true });
      openTopic(topic);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state === null, params]);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight; // the card only, never the page
  }, [state?.transcript.length, pending]);

  const ask = (question: string) => {
    if (!question.trim()) {
      setInputError(t("chat_empty"));
      input.current?.focus();
      return;
    }
    if (state && question.length > state.max_chars) {
      setInputError(t("chat_too_long", { limit: state.max_chars }));
      return;
    }
    setActiveTopic(null);
    run(() => askAida.send(question, lang), question);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask(message);
  };
  const limitReached = state?.turns_left === 0;
  const asked = state?.transcript.some((entry) => entry.role === "user");

  return (
    <section className="screen" id="ask">
      <div className="ask">
        <div className="stack-gap">
          <h1 className="h1-step">{t("ask_h1_a")} <Em>{t("ask_h1_em")}</Em></h1>
          <p>{t("ask_p")}</p>
          <div className="topics" role="group" aria-label={t("topics_label")}>
            {TOPICS.map((topic) => (
              <button key={topic} type="button" className="topic" aria-pressed={activeTopic === topic}
                disabled={busy || !state} onClick={() => openTopic(topic)}>
                <TopicIcon topic={topic} />{t(topic)}
              </button>
            ))}
          </div>
          <div className="mascot-note">
            <img className="mascot" src="/pinkai/m-open.webp" alt={t("mascot_open_alt")} />
            <span className="hand">{t("chat_disclaimer")}</span>
          </div>
        </div>

        <div className="stack-gap answer-side">
          <div className="card answer-card" id="answer-card" ref={card}>
            <div className="tape-bit" aria-hidden="true" />
            <div className="answer-head">
              <h2>{t("answer_title")}</h2><span className="hand">{t("answer_sub")}</span>
              {state && state.transcript.length > 0 && (
                <Btn variant="link" className="new-chat" disabled={busy}
                  onClick={() => { setActiveTopic(null); run(askAida.reset).then(() => input.current?.focus()); }}>
                  {t("new_conversation")}
                </Btn>
              )}
            </div>
            {loadError ? <ErrorBox error={loadError} onRetry={load} /> : !state ? <Loading /> : (
              <div className="answer conversation" ref={log} role="log" aria-label={t("chat_label")} aria-live="polite">
                {state.transcript.length === 0 && !pending && (
                  <>
                    <p>{t("answer_empty")}</p>
                    <div className="chips" role="group" aria-label={t("suggestions_label")}>
                      {["suggest_1", "suggest_2", "suggest_3"].map((key) => (
                        <button key={key} type="button" className="chip" disabled={busy || limitReached}
                          onClick={() => ask(t(key))}>{t(key)}</button>
                      ))}
                    </div>
                  </>
                )}
                {state.transcript.map((entry, index) => (
                  <div key={index} className={`entry entry-${entry.role}`}>
                    {entry.role === "topic" && <h3>{t(entry.topic!)}</h3>}
                    {entry.role === "user" && <span className="eyebrow">{t("you_asked")}</span>}
                    {/* Rendered by aida_chat.message_html: Markdown with raw HTML escaped. */}
                    <div dangerouslySetInnerHTML={{ __html: entry.html }} />
                  </div>
                ))}
                {pending && (
                  <>
                    <div className="entry entry-user"><span className="eyebrow">{t("you_asked")}</span><p dir="auto">{pending}</p></div>
                    <div className="entry typing" role="status"><span /><span /><span /><span className="sr-only">{t("aida_typing")}</span></div>
                  </>
                )}
              </div>
            )}
            <div className="answer-foot">
              <span className="hand">{t("answer_foot")}</span>
              {state && <span className="small src">{t(state.live ? "live_note" : "offline_note")}</span>}
            </div>
          </div>

          <form className="ask-form" onSubmit={submit}>
            <label htmlFor="chat-input" className="sr-only">{t("ask_own")}</label>
            <div className="askbox">
              <input id="chat-input" ref={input} value={message} dir="auto" autoComplete="off"
                maxLength={state?.max_chars ?? 500} placeholder={t("chat_placeholder")} disabled={limitReached || !state}
                aria-invalid={inputError ? true : undefined} aria-describedby={errorId}
                onChange={(event) => { setMessage(event.target.value); setInputError(null); }} />
              <Btn type="submit" disabled={busy || limitReached || !state}>{t("ask_button")}</Btn>
            </div>
            <p id={errorId} className="field-error" aria-live="assertive">{inputError}</p>
            {limitReached && <p className="small">{t("chat_turn_limit")}</p>}
            {asked && <p className="small">{t("chat_turns_left", { left: state!.turns_left })}</p>}
          </form>
        </div>
      </div>
    </section>
  );
}
