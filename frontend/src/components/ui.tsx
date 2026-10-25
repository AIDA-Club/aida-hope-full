import { ButtonHTMLAttributes, ReactNode, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

/** The design's button: rose fill with a plum offset shadow; `ghost` and `link` variants. */
export function Btn({ children, to, variant = "solid", className = "", ...rest }:
  { children: ReactNode; to?: string; variant?: "solid" | "ghost" | "link"; className?: string }
  & ButtonHTMLAttributes<HTMLButtonElement>) {
  const classes = `btn${variant === "solid" ? "" : ` ${variant}`} ${className}`.trim();
  if (to) return <Link to={to} className={classes}>{children}</Link>;
  return <button type="button" className={classes} {...rest}>{variant === "link" ? <span>{children}</span> : children}</button>;
}

/** Italic, rose emphasis with the hand-drawn underline. */
export const Em = ({ children }: { children: ReactNode }) => <span className="em">{children}</span>;

/** A handwritten margin note with the curved arrow. */
export function Note({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`note ${className}`}>
      <svg viewBox="0 0 46 34" aria-hidden="true">
        <path d="M4 4c8 20 20 26 38 22" fill="none" stroke="#C63D76" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M35 22l7 5-8 4" fill="none" stroke="#C63D76" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="hand">{children}</span>
    </div>
  );
}

export const Stamp = ({ children, className = "" }: { children: ReactNode; className?: string }) =>
  <span className={`stamp ${className}`}>{children}</span>;

/**
 * A pinned photo (white border, tape, handwritten caption). Click/tap opens it full screen;
 * Escape, the close button or a click closes it. `alt` describes the image.
 */
export function Photo({ src, alt, caption, tilt, tape = true, stamp, className = "", zoom = true }:
  { src: string; alt: string; caption?: ReactNode; tilt?: "l" | "r"; tape?: boolean; stamp?: ReactNode;
    className?: string; zoom?: boolean }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal?.();
    if (!open && element.open) element.close?.();
  }, [open]);
  const image = <img src={src} alt={alt} />;
  return (
    <figure className={`photo${tilt ? ` tilt-${tilt}` : ""} ${className}`}>
      {tape && <div className="tape-bit" aria-hidden="true" />}
      {zoom ? (
        <button ref={trigger} type="button" className="photo-zoom" onClick={() => setOpen(true)}
          aria-label={t("enlarge_image", { caption: alt })}>{image}</button>
      ) : image}
      {caption && <figcaption className="cap">{caption}</figcaption>}
      {stamp}
      {zoom && (
        <dialog ref={dialog} className="lightbox" aria-label={alt}
          onClose={() => { setOpen(false); trigger.current?.focus(); }}
          onClick={(event) => event.target === event.currentTarget && setOpen(false)}>
          {open && <img src={src} alt={alt} onClick={() => setOpen(false)} />}
          <button type="button" className="lightbox-close" onClick={() => setOpen(false)} aria-label={t("close")}>
            <Icon name="close" />
          </button>
        </dialog>
      )}
    </figure>
  );
}

/** A tick or a cross for the result ledger. */
export function Tick({ ok }: { ok: boolean | null }) {
  const { t } = useI18n();
  if (ok === null) return <span className="tick" aria-hidden="true" />;
  return ok ? (
    <svg className="tick" viewBox="0 0 30 30" role="img" aria-label={t("right")}>
      <path d="M5 16l7 7 13-16" fill="none" stroke="#1F2A33" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg className="tick" viewBox="0 0 30 30" role="img" aria-label={t("wrong")}>
      <path d="M7 7l16 16M23 7L7 23" fill="none" stroke="#B02F66" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  const id = useId();
  return (
    <label className="switch" htmlFor={id}>
      <input id={id} type="checkbox" role="switch" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="switch-track" aria-hidden="true"><span className="switch-thumb" /></span>
      <span className="switch-label">{label}</span>
    </label>
  );
}

export function Loading() {
  const { t } = useI18n();
  return (
    <div className="state-box" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{t("loading")}</span>
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div className="state-box state-error" role="alert">
      <Icon name="alert" />
      <span>{errorText(t, error)}</span>
      {onRetry && <button type="button" className="btn link" onClick={onRetry}><span>{t("try_again")}</span></button>}
    </div>
  );
}

/** The visitor-facing text for an API error: its translation key, else the generic message. */
export function errorText(t: (key: string, values?: Record<string, string | number>) => string, error: unknown) {
  if (error instanceof ApiError) {
    const text = t(error.code, error.extra as Record<string, string | number>);
    if (text !== error.code) return text;
  }
  return t("error_generic");
}

const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** A number that rolls up from 0 when it appears (the design's data-count); instant with reduced motion. */
export function CountUp({ to }: { to: number }) {
  const [value, setValue] = useState(() => (reducedMotion() ? to : 0));
  useEffect(() => {
    if (reducedMotion()) { setValue(to); return; }
    let frame = 0;
    const start = performance.now() + 350;
    const step = (now: number) => {
      const k = Math.min(1, Math.max(0, (now - start) / 900));
      setValue(Math.round(to * (1 - (1 - k) ** 3)));
      if (k < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [to]);
  return <span>{value}</span>;
}

/** A little burst of the mascot's sparkles around an element (decorative; skipped with reduced motion). */
export function sparkle(element: Element | null) {
  if (!element || reducedMotion()) return;
  const box = element.getBoundingClientRect();
  const colors = ["var(--rose)", "var(--hl)", "var(--gold)", "var(--plum)"];
  for (let i = 0; i < 14; i++) {
    const s = document.createElement("span");
    const angle = (i / 14) * 2 * Math.PI + Math.random() * 0.4;
    const distance = 50 + Math.random() * 60;
    s.className = "spark";
    s.setAttribute("aria-hidden", "true");
    s.style.left = `${box.left + box.width * (0.2 + Math.random() * 0.6)}px`;
    s.style.top = `${box.top + box.height / 2}px`;
    s.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
    s.style.setProperty("--dy", `${Math.sin(angle) * distance * 0.7}px`);
    s.style.setProperty("--c", colors[i % colors.length]);
    s.style.animationDelay = `${Math.random() * 0.15}s`;
    s.addEventListener("animationend", () => s.remove());
    document.body.append(s);
  }
}

/** The design's way of writing a probability: never "100%" or "0%" sure. */
export const pct = (x: number) => (x >= 0.995 ? ">99%" : x > 0 && x < 0.005 ? "<1%" : `${Math.round(x * 100)}%`);

/** "- one\n- two" (the Markdown lists in i18n/*.json) as plain lines. */
export const bullets = (text: string) => text.split("\n").map((line) => line.replace(/^- /, "").trim()).filter(Boolean);
