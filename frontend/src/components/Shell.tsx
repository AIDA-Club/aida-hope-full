import { Link, NavLink } from "react-router-dom";
import { useI18n } from "../i18n";

// The design's nav icons (shown only on phones, where the nav becomes a bottom tab bar).
const NAV = [
  { to: "/", key: "nav_home", end: true, icon: <path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z" /> },
  { to: "/beat", key: "nav_beat", icon: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></> },
  { to: "/tweak", key: "nav_tweak", icon: <><path d="M3 7h11M19 7h2M3 17h4M11 17h10" /><circle cx="16.5" cy="7" r="2.5" /><circle cx="8.5" cy="17" r="2.5" /></> },
  { to: "/ask", key: "nav_ask", icon: <path d="M4 5h16v11H10l-6 4z" /> },
  { to: "/about", key: "nav_about", icon: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></> },
];

/** The pink awareness ribbon: one flat pink, a gap where the strands cross, notched tails. */
export function Ribbon() {
  const pink = "#EC5A9B";
  return (
    <svg viewBox="0 0 100 140" aria-hidden="true">
      <defs>
        {/* the front strand cuts a gap through the strand behind it */}
        <mask id="ribbon-gap" maskUnits="userSpaceOnUse">
          <rect width="100" height="140" fill="#fff" />
          <path d="M38 54 L80 130" stroke="#000" strokeWidth="21" />
        </mask>
        {/* V-shaped notches in both tails */}
        <mask id="ribbon-tails" maskUnits="userSpaceOnUse">
          <rect width="100" height="140" fill="#fff" />
          <path d="M10.5 121.9 L25.4 119.9 L31.5 133.5 Z M89.5 121.9 L74.6 119.9 L68.5 133.5 Z" fill="#000" />
        </mask>
      </defs>
      <g mask="url(#ribbon-tails)" fill="none" stroke={pink} strokeWidth="15">
        <path mask="url(#ribbon-gap)" d="M50 8 C74 8 72 36 62 54 L22 126" />
        <path d="M50 8 C26 8 28 36 38 54 L78 126" />
      </g>
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
        <LanguageToggle />
        <nav className="nav" aria-label={t("nav_label")}>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <svg className="ni" viewBox="0 0 24 24" aria-hidden="true">{item.icon}</svg>
              <span className="full">{t(item.key)}</span>
              <span className="short">{t(`${item.key}_short`)}</span>
            </NavLink>
          ))}
        </nav>
      </header>
    </>
  );
}

export function Footer() {
  const { t } = useI18n();
  return (
    <footer>
      <span className="warn"><b>{t("footer_brand")}</b>{t("footer_warn")}</span>
      <span>{t("footer_credits")}</span>
    </footer>
  );
}
