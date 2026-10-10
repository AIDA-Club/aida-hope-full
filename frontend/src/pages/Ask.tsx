import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { askAida, ChatState } from "../api";
import { Icon, IconName } from "../components/Icon";
import { Footer, Hero } from "../components/Shell";
import { ErrorBox, errorText, Loading } from "../components/ui";
import { useI18n } from "../i18n";

const TOPICS: Array<{ key: string; icon: IconName; tone: string }> = [
  { key: "know_signs", icon: "search", tone: "pink" },
  { key: "myth_fact", icon: "question", tone: "lilac" },
  { key: "explain_term", icon: "book", tone: "peach" },
  { key: "get_help", icon: "pin", tone: "blue" },
];

export default function Ask() {
  const { t, lang } = useI18n();
  const [state, setState] = useState<ChatState | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const errorId = useId();

  const load = () => {
    setLoadError(null);
    askAida.state().then(setState).catch(setLoadError);
  };
  useEffect(load, []);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight; // the log only, never the page
  }, [state?.transcript.length, pending]);

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
    run(() => askAida.send(question, lang), question);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask(message);
  };

  const limitReached = state?.turns_left === 0;

  return (
    <div className="page page-ask">
      <Hero
        title={<><span className="line">{t("ask_headline_1")}</span> <span className="line">{t("ask_headline_2")}</span></>}
        sub={t("ask_sub")} mascot="/art/mascot-ask-wave-wink.webp" ribbon="/art/ribbon-ask.webp" className="hero-ask" />

      <nav className="topics" aria-label={t("topics_label")}>
        {TOPICS.map((topic) => (
          <button key={topic.key} type="button" className={`topic tone-${topic.tone}`} disabled={busy || !state}
            onClick={() => run(() => askAida.topic(topic.key, lang))}>
            <span className="topic-icon"><Icon name={topic.icon} size={56} strokeWidth={1.8} />
              <span className={`badge-rays rays-${topic.tone}`} /></span>
            <span className="topic-title">{t(topic.key)}</span>
            <span className="topic-arrow"><Icon name="arrow" size={22} /></span>
          </button>
        ))}
      </nav>

      <section className="panel chat-panel" aria-labelledby="chat-title">
        <div className="chat-main">
          <header className="chat-head">
            <img className="avatar" src="/art/avatar-neutral.webp" alt="" />
            <div>
              <h2 id="chat-title">{t("ask_title")}</h2>
              <p>{t("companion")}</p>
            </div>
            <button type="button" className="new-chat" disabled={busy || !state}
              onClick={() => run(askAida.reset).then(() => input.current?.focus())}>
              <Icon name="plus" />{t("new_conversation")}
            </button>
          </header>

          {loadError ? <ErrorBox error={loadError} onRetry={load} /> : !state ? <Loading /> : (
            <div className="chat-log" ref={log} role="log" aria-label={t("chat_label")} aria-live="polite">
              <div className="msg msg-aida">
                <img className="avatar avatar-sm" src="/art/avatar-smiling.webp" alt="" />
                <div className="bubble-aida">
                  <p className="greet-title">{t("greeting")}</p>
                  <p>{t("greeting_sub")}</p>
                </div>
              </div>
              {state.transcript.length === 0 && (
                <div className="suggestions" role="group" aria-label={t("suggestions_label")}>
                  {["suggest_1", "suggest_2", "suggest_3"].map((key) => (
                    <button key={key} type="button" className="chip" disabled={busy || limitReached}
                      onClick={() => ask(t(key))}>{t(key)}</button>
                  ))}
                </div>
              )}
              {state.transcript.map((entry, index) => (
                <div key={index} className={`msg msg-${entry.role}`}>
                  {entry.role !== "user" && entry.role !== "notice" && (
                    <img className="avatar avatar-sm" src="/art/avatar-smiling.webp" alt="" />
                  )}
                  <div className={entry.role === "user" ? "bubble-user" : "bubble-aida"}>
                    <span className="sr-only">{t(entry.role === "user" ? "you_said" : "aida_said")}: </span>
                    {entry.role === "topic" && <p className="topic-heading">{t(entry.topic!)}</p>}
                    {/* Rendered by aida_chat.message_html: Markdown with raw HTML escaped. */}
                    <div dangerouslySetInnerHTML={{ __html: entry.html }} />
                  </div>
                </div>
              ))}
              {pending && (
                <>
                  <div className="msg msg-user"><div className="bubble-user"><p dir="auto">{pending}</p></div></div>
                  <div className="msg msg-assistant" role="status">
                    <img className="avatar avatar-sm" src="/art/avatar-smiling.webp" alt="" />
                    <div className="bubble-aida typing"><span /><span /><span /><span className="sr-only">{t("aida_typing")}</span></div>
                  </div>
                </>
              )}
            </div>
          )}

          {limitReached && <p className="note-blue"><Icon name="info" />{t("chat_turn_limit")}</p>}
          <form className="chat-form" onSubmit={submit}>
            <Icon name="chat" className="chat-form-icon" />
            <label className="sr-only" htmlFor="chat-input">{t("chat_placeholder")}</label>
            <input id="chat-input" ref={input} value={message} dir="auto" autoComplete="off"
              maxLength={state?.max_chars ?? 500} placeholder={t("chat_placeholder")} disabled={limitReached || !state}
              aria-invalid={inputError ? true : undefined} aria-describedby={`${errorId} chat-disclaimer`}
              onChange={(event) => { setMessage(event.target.value); setInputError(null); }} />
            <button type="submit" className="send" disabled={busy || limitReached || !state} aria-label={t("send")}>
              <Icon name="send" />
            </button>
          </form>
          <p id={errorId} className="field-error" aria-live="assertive">{inputError}</p>
          <div className="chat-notes">
            <p id="chat-disclaimer"><Icon name="warning" size={16} />{t("chat_disclaimer")}</p>
            {state && <p>{t(state.live ? "live_note" : "offline_note")}</p>}
            {state && state.transcript.some((entry) => entry.role === "user") && (
              <p>{t("chat_turns_left", { left: state.turns_left })}</p>
            )}
          </div>
        </div>
        <aside className="curiosity" aria-labelledby="curiosity-title">
          <img src="/art/mascot-curiosity.webp" alt="" />
          <h2 id="curiosity-title">{t("curiosity_title")}</h2>
          <p>{t("curiosity_text")}</p>
        </aside>
      </section>
      <Footer />
    </div>
  );
}
