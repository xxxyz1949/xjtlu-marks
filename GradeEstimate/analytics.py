from __future__ import annotations

import streamlit as st


@st.cache_resource
def _runtime_counter() -> dict:
    return {
        "total_visits": 0,
        "total_predictions": 0,
    }


def register_visit() -> None:
    if "session_predictions" not in st.session_state:
        st.session_state["session_predictions"] = 0

    if not st.session_state.get("visit_registered", False):
        stats = _runtime_counter()
        stats["total_visits"] += 1
        st.session_state["visit_registered"] = True


def register_prediction() -> None:
    stats = _runtime_counter()
    stats["total_predictions"] += 1
    st.session_state["session_predictions"] = st.session_state.get("session_predictions", 0) + 1


def snapshot() -> dict:
    stats = _runtime_counter()
    return {
        "total_visits": int(stats.get("total_visits", 0)),
        "total_predictions": int(stats.get("total_predictions", 0)),
        "session_predictions": int(st.session_state.get("session_predictions", 0)),
    }
