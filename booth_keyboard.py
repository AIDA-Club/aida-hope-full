"""Local keyboard controls; R/C are reserved by the native Streamlit API."""
import json

import streamlit as st

from booth import t


def shortcuts() -> None:
    # Find only currently visible, enabled buttons. A constant listener avoids
    # losing a quick keypress while the next phase's iframe is loading.
    targets = {"escape": ["next_visitor"], "n": ["first_normal", "final_normal"],
               "b": ["first_benign", "final_benign"], "m": ["first_malignant", "final_malignant"],
               "r": ["reveal_ai"], "k": ["keep_answer"], "c": ["change_answer"], "t": ["reveal_truth"]}
    st.iframe("""<script>
    const doc = window.parent.document;
    const host = window.parent;
    const targets = """ + json.dumps(targets) + """;
    if (host.__aidaBoothKeyHandler) {
        doc.removeEventListener('keydown', host.__aidaBoothKeyHandler, true);
    }
    const handler = (event) => {
        if (event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
        const editing = event.target.closest && event.target.closest(
            'input, textarea, select, [contenteditable="true"], [role="slider"]');
        if (editing) return;
        const key = event.code.startsWith('Key') ? event.code.slice(3).toLowerCase()
                                                : event.key.toLowerCase();
        const choices = targets[key];
        if (!choices) return;
        const button = choices.map(target => doc.querySelector('.st-key-' + target + ' button'))
            .find(candidate => candidate && !candidate.disabled && candidate.getClientRects().length);
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        button.click();
    };
    host.__aidaBoothKeyHandler = handler;
    doc.addEventListener('keydown', handler, true);
    const cleanup = () => {
        doc.removeEventListener('keydown', handler, true);
        if (host.__aidaBoothKeyHandler === handler) delete host.__aidaBoothKeyHandler;
    };
    window.addEventListener('pagehide', cleanup, {once: true});
    window.addEventListener('beforeunload', cleanup, {once: true});
    </script>""", height=1, width=1, tab_index=-1, alt=t("keyboard_controls"))
