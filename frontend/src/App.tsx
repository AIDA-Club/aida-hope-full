import { useEffect, useRef } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { ApiError } from "./api";
import { Footer, Header } from "./components/Shell";
import { ErrorBox, Loading } from "./components/ui";
import { useI18n } from "./i18n";
import About from "./pages/About";
import Ask from "./pages/Ask";
import Beat from "./pages/Beat";
import Home from "./pages/Home";
import Tweak from "./pages/Tweak";

const TITLES: Record<string, string> = { "/beat": "nav_beat", "/tweak": "nav_tweak", "/ask": "nav_ask", "/about": "nav_about" };

export default function App() {
  const { t, ready, failed, retry } = useI18n();
  const location = useLocation();

  useEffect(() => {
    const key = TITLES[location.pathname];
    document.title = key && ready ? `${t(key)} · PinkAI` : "PinkAI — AIDA";
  }, [location.pathname, ready, t]);

  // After a client-side navigation, move focus to the new page (not on first load, so the
  // first Tab still reaches the skip link).
  const previousPath = useRef(location.pathname);
  useEffect(() => {
    if (previousPath.current === location.pathname) return;
    previousPath.current = location.pathname;
    window.scrollTo(0, 0);
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <>
      <a className="skip-link" href="#main">{t("skip_link")}</a>
      <Header />
      <main id="main" tabIndex={-1}>
        {!ready ? (
          <section className="screen">{failed ? <ErrorBox error={new ApiError("error_offline", 0)} onRetry={retry} /> : <Loading />}</section>
        ) : (
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/beat" element={<Beat />} />
            <Route path="/tweak" element={<Tweak />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<Home />} />
          </Routes>
        )}
      </main>
      <Footer />
    </>
  );
}
