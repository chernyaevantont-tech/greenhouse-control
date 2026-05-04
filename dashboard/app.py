"""Streamlit real-time dashboard for the Greenhouse Control system.

Run with:
    streamlit run dashboard/app.py -- --broker localhost --port 1883
"""

from __future__ import annotations

import argparse
import sys
from collections import deque

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dashboard.config import MQTT_HOST, MQTT_PORT, WINDOW_SIZE
from dashboard.mqtt_listener import DashboardMQTTListener

# ---------------------------------------------------------------------------
# Parse CLI args before any st.* calls to avoid conflicts with Streamlit's
# own argument parser.
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--broker", default=MQTT_HOST)
_parser.add_argument("--port", type=int, default=MQTT_PORT)
_args, _ = _parser.parse_known_args(sys.argv[1:])

BROKER = _args.broker
PORT = _args.port

# ---------------------------------------------------------------------------
# Default session state
# ---------------------------------------------------------------------------

DEFAULT_STATE: dict = {
    # Rolling buffers
    "steps": deque(maxlen=WINDOW_SIZE),
    "t_in": deque(maxlen=WINDOW_SIZE),
    "co2": deque(maxlen=WINDOW_SIZE),
    "rh": deque(maxlen=WINDOW_SIZE),
    "T_out": deque(maxlen=WINDOW_SIZE),
    "rad": deque(maxlen=WINDOW_SIZE),
    "uBoil": deque(maxlen=WINDOW_SIZE),
    "uCO2": deque(maxlen=WINDOW_SIZE),
    "uThScr": deque(maxlen=WINDOW_SIZE),
    "uVent": deque(maxlen=WINDOW_SIZE),
    "uLamp": deque(maxlen=WINDOW_SIZE),
    "uBlScr": deque(maxlen=WINDOW_SIZE),
    "mahal_dist": deque(maxlen=WINDOW_SIZE),
    "ood_threshold": 3.0,
    "in_distribution": deque(maxlen=WINDOW_SIZE),
    # Agent decision log (most-recent 50)
    "agent_log": deque(maxlen=50),
    # Connection status
    "mqtt_connected": False,
}

# Module-level plain dict used by MQTT listener (background thread safe).
# Paho callbacks write here; the main thread copies to st.session_state.
_mqtt_data: dict = {
    k: (deque(v, maxlen=v.maxlen) if isinstance(v, deque) else v)
    for k, v in DEFAULT_STATE.items()
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Greenhouse Control Dashboard", layout="wide")

# ---------------------------------------------------------------------------
# Initialise state and MQTT listener exactly once per session
# ---------------------------------------------------------------------------

if "_listener" not in st.session_state:
    listener = DashboardMQTTListener(
        host=BROKER, port=PORT, session_state=_mqtt_data
    )
    listener.start()
    st.session_state["_listener"] = listener

# Sync shared data from the thread-safe plain dict into session_state
for _k, _v in _mqtt_data.items():
    st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# Auto-refresh every 2 seconds so new MQTT data is rendered
# ---------------------------------------------------------------------------

st_autorefresh(interval=2000, key="dashboard_refresh")

ss = st.session_state

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🌱 Greenhouse Control — Live Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("MQTT", "🟢 Connected" if ss["mqtt_connected"] else "🔴 Offline")
c2.metric("Current Step", ss["steps"][-1] if ss["steps"] else "—")
c3.metric(
    "t_in",
    f"{ss['t_in'][-1]:.1f} °C" if ss["t_in"] else "—",
    delta=f"{ss['t_in'][-1] - 20.0:+.1f}" if ss["t_in"] else None,
)
c4.metric(
    "CO₂",
    f"{ss['co2'][-1]:.0f} ppm" if ss["co2"] else "—",
    delta=f"{ss['co2'][-1] - 800.0:+.0f}" if ss["co2"] else None,
)

st.divider()

# ---------------------------------------------------------------------------
# Main layout: two columns
# ---------------------------------------------------------------------------

col_left, col_right = st.columns([0.6, 0.4])

# ── Left column: tabbed charts ──────────────────────────────────────────────

with col_left:
    tab_thermo, tab_actuators = st.tabs(["📊 Thermodynamics", "🎛️ Actuators"])

    # -- Tab 1: Thermodynamics -----------------------------------------------
    with tab_thermo:
        if ss["steps"]:
            df = pd.DataFrame(
                {
                    "step": list(ss["steps"]),
                    "t_in": list(ss["t_in"]),
                    "co2": list(ss["co2"]),
                    "rh": list(ss["rh"]),
                    "T_out": list(ss["T_out"]),
                }
            )

            # Temperature
            fig_t = px.line(
                df,
                x="step",
                y=["t_in", "T_out"],
                labels={"value": "°C"},
                title="Temperature",
            )
            fig_t.add_hline(
                y=20.0,
                line_dash="dash",
                annotation_text="Setpoint 20°C",
            )
            fig_t.add_hrect(y0=18, y1=22, fillcolor="green", opacity=0.05)
            st.plotly_chart(fig_t, use_container_width=True)

            # CO2
            fig_co2 = px.line(df, x="step", y="co2", title="CO₂ (ppm)")
            fig_co2.add_hline(
                y=800, line_dash="dash", annotation_text="Setpoint 800 ppm"
            )
            fig_co2.add_hrect(y0=600, y1=1000, fillcolor="green", opacity=0.05)
            st.plotly_chart(fig_co2, use_container_width=True)

            # Relative humidity
            fig_rh = px.line(df, x="step", y="rh", title="Relative Humidity (%)")
            fig_rh.add_hline(
                y=85,
                line_color="red",
                line_dash="dot",
                annotation_text="Max 85%",
            )
            st.plotly_chart(fig_rh, use_container_width=True)
        else:
            st.info("Waiting for telemetry data…")

    # -- Tab 2: Actuators ----------------------------------------------------
    with tab_actuators:
        ACTUATORS = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]
        LABELS = [
            "Boiler",
            "CO₂ Inject",
            "Thermal Screen",
            "Ventilation",
            "Lamps",
            "Blackout Screen",
        ]

        if ss["steps"]:
            steps_list = list(ss["steps"])
            cols = st.columns(3)
            for i, (key, label) in enumerate(zip(ACTUATORS, LABELS)):
                with cols[i % 3]:
                    fig = px.area(
                        x=steps_list,
                        y=list(ss[key]),
                        range_y=[0, 1],
                        title=label,
                        labels={"x": "step", "y": "signal [0–1]"},
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Waiting for actuator data…")

# ── Right column: OOD monitor + supervisor log ───────────────────────────────

with col_right:
    # OOD Monitor
    st.subheader("OOD Monitor")
    if ss["mahal_dist"]:
        df_ood = pd.DataFrame(
            {
                "step": list(ss["steps"]),
                "mahal": list(ss["mahal_dist"]),
            }
        )
        threshold = ss["ood_threshold"]

        fig_ood = px.line(
            df_ood,
            x="step",
            y="mahal",
            title="OOD Mahalanobis Distance",
            labels={"mahal": "Distance (σ)"},
        )
        fig_ood.add_hline(
            y=threshold,
            line_color="orange",
            line_dash="dash",
            annotation_text=f"Retraining Threshold ({threshold:.1f}σ)",
        )
        fig_ood.add_hrect(y0=0, y1=threshold, fillcolor="green", opacity=0.05)
        fig_ood.add_hrect(
            y0=threshold,
            y1=threshold * 3,
            fillcolor="red",
            opacity=0.05,
        )

        n_ood = sum(1 for v in ss["in_distribution"] if not v)
        st.metric("OOD Events in Window", n_ood, delta=None, delta_color="inverse")
        st.plotly_chart(fig_ood, use_container_width=True)
    else:
        st.info("Waiting for OOD metrics…")

    st.divider()

    # Supervisor Log
    st.subheader("Supervisor Decisions")
    if ss["agent_log"]:
        log_df = pd.DataFrame(list(ss["agent_log"]))
        st.dataframe(
            log_df[["step", "status", "decision", "confidence", "reason"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Waiting for Supervisor decisions…")
