import { NavLink, Link } from "react-router-dom";
import { useI18n } from "../i18n";

const NAV = [
  { to: "/", key: "nav_home", end: true },
  { to: "/beat", key: "nav_beat" },
  { to: "/tweak", key: "nav_tweak" },
  { to: "/ask", key: "nav_ask" },
  { to: "/about", key: "nav_about" },
];

/** The pink awareness ribbon from the PinkAI design. */
export function Ribbon({ label }: { label?: string }) {
  return (
    <svg className="ribbon" viewBox="0 0 34 44" role={label ? "img" : undefined} aria-label={label}
      aria-hidden={label ? undefined : true}>
      <path d="M17 2c-6 0-10 5-10 10 0 6 5 10 10 17 5-7 10-11 10-17 0-5-4-10-10-10zm0 5c3 0 5 2.5 5 5 0 3-2.5 6-5 10-2.5-4-5-7-5-10 0-2.5 2-5 5-5z" fill="#C63D76" />
      <path d="M12 22 4 40c-.6 1.3.3 2.6 1.6 2.4l5.4-1.2L20 24.5 12 22z" fill="#C63D76" />
      <path d="M22 22l8 18c.6 1.3-.3 2.6-1.6 2.4L23 41.2 14 24.5 22 22z" fill="#7A1F46" />
    </svg>
  );
}

function LanguageToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <div className="lang" role="group" aria-label={t("language_switch")}>
      <button type="button" lang="en" aria-pressed={lang === "en"} onClick={() => setLang("en")}>{t("lang_en")}</button>
      <button type="button" lang="ar" aria-pressed={lang === "ar"} onClick={() => setLang("ar")}>العربية</button>
    </div>
  );
}

export function Header() {
  const { t } = useI18n();
  return (
    <>
      <div className="tape" aria-hidden="true" />
      <header className="top">
        <Link to="/" className="brand" aria-label={t("brand_home")}>
          <Ribbon />
          <img src="/pinkai/aida-logo-pink.webp" alt={t("logo_alt")} width={550} height={176} />
        </Link>
        <nav className="nav" aria-label={t("nav_label")}>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}
              className={({ isActive }) => (isActive ? "is-current" : undefined)}>
              {t(item.key)}
            </NavLink>
          ))}
        </nav>
        <LanguageToggle />
      </header>
    </>
  );
}

export function Footer() {
  const { t } = useI18n();
  return (
    <footer className="foot">
      <span className="warn"><b>{t("footer_brand")}</b>{t("footer_warn")}</span>
      <span>{t("footer_credits")}</span>
    </footer>
  );
}
