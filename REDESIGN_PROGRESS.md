# Redesign progress checklist

- [x] Read brief, references, assets, existing code; baseline tests (91 passed) at `5a09062`
- [x] FastAPI layer over the existing functions; Challenge/Tweak rules shared with Streamlit
- [x] React + TS shell (header, language toggle, footer, hero) and token system
- [x] Home · Beat intro · Choose · AI reveal · Truth · End · Tweak · Ask · About
- [x] Arabic RTL, tablet and phone layouts, error/loading states
- [x] API tests incl. exact prediction parity (`tests/test_api.py`), frontend unit tests
- [x] Playwright screenshots + flows (`scripts/redesign_screens.py`), 63/63
- [x] Two visual comparison passes against `design/reference/`
- [x] README commands, DESIGN_MAP.md, IMPLEMENTATION_REPORT.md
- [ ] Live Ask AIDA with a real key (needs a key; not available here)
- [ ] Native review of the draft Arabic strings in `frontend/src/i18n/redesign.ar.json`
