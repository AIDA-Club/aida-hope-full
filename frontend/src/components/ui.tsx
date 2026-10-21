import { ButtonHTMLAttributes, ReactNode, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api";
import { useI18n } from "../i18n";
import { Icon, IconName } from "./Icon";

type Tone = "pink" | "lilac" | "peach" | "blue";

/** A pastel circle with a line icon and the little "rays" accent from the references. */
export function IconBadge({ icon, tone = "pink", size = "md", rays = true }:
  { icon: IconName; tone?: Tone; size?: "sm" | "md" | "lg"; rays?: boolean }) {
  return (
    <span className={`badge badge-${tone} badge-${size}`} aria-hidden="true">
      <Icon name={icon} />
      {rays && <span className={`badge-rays rays-${tone}`} />}
    </span>
  );
}

interface CtaProps {
  children: ReactNode;
  to?: string;
  arrow?: "circle" | "plain" | false;
  variant?: "primary" | "outline" | "soft";
  size?: "md" | "lg";
  className?: string;
}

/** The burgundy-pink pill button. Renders a router link when `to` is given. */
export function Cta({ children, to, arrow = "circle", variant = "primary", size = "md", className = "",
  ...rest }: CtaProps & ButtonHTMLAttributes<HTMLButtonElement>) {
  const classes = `cta cta-${variant} cta-${size} ${arrow === "circle" ? "has-arrow" : ""} ${className}`;
  const inner = (
    <>
      <span className="cta-label">{children}</span>
      {arrow === "circle" && <span className="cta-arrow"><Icon name="arrow" size={22} /></span>}
      {arrow === "plain" && <Icon name="arrow" size={24} className="cta-plain-arrow" />}
    </>
  );
  if (to) return <Link to={to} className={classes}>{inner}</Link>;
  return <button type="button" className={classes} {...rest}>{inner}</button>;
}

export function ProbabilityBar({ label, value, emphasis = false }: { label: string; value: number; emphasis?: boolean }) {
  const percent = Math.max(0, Math.min(100, value * 100));
  return (
    <div className={`prob${emphasis ? " prob-strong" : ""}`}>
      <div className="prob-label">{label}</div>
      <div className="prob-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={Math.round(percent)}>
        <div className="prob-fill" style={{ width: `${Math.max(percent, 1.2)}%` }} />
      </div>
    </div>
  );
}

/** An image that opens full screen; Escape, the close button or a click closes it. */
export function ZoomImage({ src, alt, caption, className = "", hint = true }:
  { src: string; alt: string; caption?: ReactNode; className?: string; hint?: boolean }) {
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
  return (
    <figure className={`zoom ${className}`}>
      <button ref={trigger} type="button" className="zoom-trigger" onClick={() => setOpen(true)}
        aria-label={t("enlarge_image", { caption: alt })}>
        <img src={src} alt={alt} />
      </button>
      {(caption || hint) && (
        <figcaption className="zoom-caption">
          {caption}
          {hint && (
            <button type="button" className="zoom-hint" onClick={() => setOpen(true)} tabIndex={-1}>
              {t("tap_enlarge")} <Icon name="expand" size={16} />
            </button>
          )}
        </figcaption>
      )}
      <dialog ref={dialog} className="lightbox" aria-label={alt}
        onClose={() => { setOpen(false); trigger.current?.focus(); }}
        onClick={(event) => event.target === event.currentTarget && setOpen(false)}>
        {open && <img src={src} alt={alt} onClick={() => setOpen(false)} />}
        <button type="button" className="lightbox-close" onClick={() => setOpen(false)} aria-label={t("close")}>
          <Icon name="close" />
        </button>
      </dialog>
    </figure>
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
      {onRetry && <button type="button" className="link-button" onClick={onRetry}>{t("try_again")}</button>}
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
