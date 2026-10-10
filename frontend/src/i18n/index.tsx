import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { translationsFor } from "../api";
import { format, splitTemplate, Values } from "../format";
import redesignAr from "./redesign.ar.json";
import redesignEn from "./redesign.en.json";

export type Lang = "en" | "ar";
const LOCAL: Record<Lang, Record<string, string>> = { en: redesignEn, ar: redesignAr };
const STORAGE_KEY = "aida-lang";

export interface I18n {
  lang: Lang;
  dir: "ltr" | "rtl";
  setLang: (lang: Lang) => void;
  t: (key: string, values?: Values) => string;
  /** A translated template with React nodes in place of some fields. */
  tn: (key: string, nodes: Record<string, ReactNode>, values?: Values) => ReactNode;
  ready: boolean;
  failed: boolean;
  retry: () => void;
}

const Context = createContext<I18n | null>(null);

function storedLang(): Lang {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("lang");
    if (fromUrl === "ar" || fromUrl === "en") return fromUrl;
    return window.localStorage.getItem(STORAGE_KEY) === "ar" ? "ar" : "en";
  } catch {
    return "en";
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(storedLang);
  const [remote, setRemote] = useState<Partial<Record<Lang, Record<string, string>>>>({});
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Both languages are small: load the other one too, so switching is instant.
    let live = true;
    setFailed(false);
    for (const code of [lang, lang === "en" ? "ar" : "en"] as Lang[]) {
      if (remote[code]) continue;
      translationsFor(code)
        .then((strings) => live && setRemote((current) => ({ ...current, [code]: strings })))
        .catch(() => live && code === lang && setFailed(true));
    }
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, attempt]);

  const dir = lang === "ar" ? "rtl" : "ltr";
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private mode: the choice lasts for this page only */
    }
  }, []);

  const value = useMemo<I18n>(() => {
    const strings = { ...(remote[lang] ?? {}), ...LOCAL[lang] };
    const raw = (key: string) => strings[key] ?? key;
    return {
      lang,
      dir,
      setLang,
      ready: Boolean(remote[lang]),
      failed,
      retry: () => setAttempt((n) => n + 1),
      t: (key, values) => format(raw(key), values),
      tn: (key, nodes, values) =>
        splitTemplate(raw(key)).map((part, index) =>
          "text" in part ? <span key={index}>{part.text}</span>
            : part.field in nodes ? <span key={index}>{nodes[part.field]}</span>
            : <span key={index}>{format(`{${part.field}${part.digits ? `:.${part.digits}f` : ""}}`, values)}</span>),
    };
  }, [lang, dir, remote, failed, setLang]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useI18n(): I18n {
  const context = useContext(Context);
  if (!context) throw new Error("useI18n outside I18nProvider");
  return context;
}
