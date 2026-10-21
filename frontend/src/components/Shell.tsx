import { ReactNode, useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

const NAV = [
  { to: "/", key: "nav_home", end: true },
  { to: "/beat", key: "nav_beat" },
  { to: "/tweak", key: "nav_tweak" },
  { to: "/ask", key: "nav_ask" },
  { to: "/about", key: "nav_about" },
];

export function Wordmark() {
  return (
    <span className="wordmark" dir="ltr">
      <svg className="wordmark-rays" viewBox="0 0 20 24" aria-hidden="true">
        <path d="M13 4.5 16.5 1.5M10.5 9.5H16M13 14.5l3.5 3" />
      </svg>
      <span className="wordmark-name">
        <span className="wordmark-pink">Pink</span><span className="wordmark-ai">AI</span>
      </span>
    </span>
  );
}

function LanguageToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <div className="lang-toggle" role="group" aria-label={t("language_switch")}>
      <button type="button" lang="en" aria-pressed={lang === "en"} onClick={() => setLang("en")}>EN</button>
      <button type="button" lang="ar" aria-pressed={lang === "ar"} onClick={() => setLang("ar")}>العربية</button>
    </div>
  );
}

export function Header() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="site-header">
      <Link to="/" className="brand" aria-label={t("brand_home")}>
        <Wordmark />
      </Link>
      <button
        ref={menuButton}
        type="button"
        className="menu-button"
        aria-expanded={open}
        aria-controls="site-nav"
        aria-label={t(open ? "menu_close" : "menu_open")}
        onClick={() => setOpen((value) => !value)}
      >
        <Icon name={open ? "close" : "menu"} />
      </button>
      <nav id="site-nav" className={`site-nav${open ? " is-open" : ""}`} aria-label={t("nav_label")}>
        <ul>
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end}>{t(item.key)}</NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <LanguageToggle />
    </header>
  );
}

export function Footer({ credits, extra }: { credits?: ReactNode; extra?: ReactNode }) {
  const { t } = useI18n();
  return (
    <footer className="site-footer">
      <div className="footer-rule">
        <span className="footer-line" aria-hidden="true" />
        <p className="footer-disclaimer">{t("disclaimer")}</p>
        <span className="footer-line" aria-hidden="true" />
        {extra}
      </div>
      {credits && <p className="footer-credits">{credits}</p>}
    </footer>
  );
}

interface HeroProps {
  title: ReactNode;
  sub?: ReactNode;
  mascot: string;
  ribbon: string;
  mascotAlt?: string;
  children?: ReactNode;
  className?: string;
  sparkles?: "pink" | "peach" | "both";
}

/** Page header: eyebrow chip, big title, subtitle, and the mascot with its ribbon (decorative). */
export function Hero({ title, sub, mascot, ribbon, children, className = "", sparkles = "both" }: HeroProps) {
  const { t } = useI18n();
  return (
    <section className={`hero ${className}`}>
      <div className="hero-text">
        <p className="eyebrow">{t("eyebrow_fair")}</p>
        <h1 className="hero-title">{title}</h1>
        {sub && <p className="hero-sub">{sub}</p>}
        {children}
      </div>
      <div className="hero-art" aria-hidden="true">
        <img className="hero-petal" src="/art/decoration-pink-petal.webp" alt="" />
        <img className="hero-ribbon" src={ribbon} alt="" />
        <img className="hero-rays" src="/art/decoration-three-rays.webp" alt="" />
        {sparkles !== "peach" && <img className="hero-spark hero-spark-pink" src="/art/decoration-sparkle-raspberry.webp" alt="" />}
        {sparkles !== "pink" && <img className="hero-spark hero-spark-peach" src="/art/decoration-sparkle-peach.webp" alt="" />}
        <img className="hero-mascot" src={mascot} alt="" />
      </div>
    </section>
  );
}
