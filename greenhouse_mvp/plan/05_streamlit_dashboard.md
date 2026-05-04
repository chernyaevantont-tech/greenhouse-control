# Plan 05: Streamlit Real-Time Dashboard (`dashboard/app.py`)

## Overview

The dashboard is a **fully decoupled MQTT subscriber**. It has zero imports from
`control_core`, `orchestration`, or `environment`. It knows only about:

- The MQTT broker address and topic names.
- The Pydantic schemas (imported from `orchestration/schemas.py`) to deserialise
  incoming payloads.
- Streamlit for rendering.

This clean boundary means the dashboard can be started, stopped, or crashed
without affecting the control loop in any way.

---

## 1. File Structure

```
dashboard/
├── app.py            # Streamlit entry point
├── mqtt_listener.py  # Background MQTT thread + st.session_state writer
└── config.py         # Topic names, broker address, rolling-window size
```

---

## 2. MQTT Topics Consumed

| Topic | Schema | Used for |
|---|---|---|
| `greenhouse/telemetry` | `TelemetryPayload` | Thermodynamics charts |
| `greenhouse/action/approved` | `ActionPayload` | Actuator charts |
| `greenhouse/ood/metrics` | `OODMetrics` | OOD Error chart |
| `greenhouse/supervisor/verdict` | `SupervisorVerdict` | Agent Thoughts log |

> The dashboard subscribes to the **approved** action topic, not the proposed one,
> so it reflects what was actually applied to the simulation.

---

## 3. Session State Schema

`st.session_state` is the in-memory rolling store. All MQTT callbacks write to it;
all Streamlit render functions read from it.

```python
# Initialised once on first run
DEFAULT_STATE = {
    # Rolling buffers (deque with maxlen = WINDOW_SIZE, default 576 = 1 day)
    "steps":       deque(maxlen=WINDOW_SIZE),   # int
    "t_in":        deque(maxlen=WINDOW_SIZE),   # °C
    "co2":         deque(maxlen=WINDOW_SIZE),   # ppm
    "rh":          deque(maxlen=WINDOW_SIZE),   # %
    "T_out":       deque(maxlen=WINDOW_SIZE),   # °C (external)
    "rad":         deque(maxlen=WINDOW_SIZE),   # W/m²
    "uBoil":       deque(maxlen=WINDOW_SIZE),
    "uCO2":        deque(maxlen=WINDOW_SIZE),
    "uThScr":      deque(maxlen=WINDOW_SIZE),
    "uVent":       deque(maxlen=WINDOW_SIZE),
    "uLamp":       deque(maxlen=WINDOW_SIZE),
    "uBlScr":      deque(maxlen=WINDOW_SIZE),
    "mahal_dist":  deque(maxlen=WINDOW_SIZE),   # OOD Mahalanobis distance
    "ood_threshold": 3.0,                       # scalar, updated from OODMetrics
    "in_distribution": deque(maxlen=WINDOW_SIZE),  # bool
    # Agent log (most-recent N verdicts)
    "agent_log":   deque(maxlen=50),            # list of dicts
    # Connection status
    "mqtt_connected": False,
}
```

---

## 4. Background MQTT Listener (`dashboard/mqtt_listener.py`)

Streamlit runs in the main thread. MQTT must run in a **daemon background thread**
so it does not block the UI. `st.session_state` is safe to write from other threads
in Streamlit ≥ 1.28 (it is a thread-local proxy that ultimately writes to a
server-side session store).

```python
class DashboardMQTTListener:
    def __init__(self, host: str, port: int, session_state):
        self._ss = session_state   # reference to st.session_state
        self._client = mqtt.Client()
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message
        self._client.connect(host, port)

    def start(self) -> None:
        """Start non-blocking network loop in its own thread."""
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
```

### `_on_connect`

```python
def _on_connect(self, client, userdata, flags, rc):
    self._ss["mqtt_connected"] = (rc == 0)
    client.subscribe("greenhouse/telemetry",         qos=0)
    client.subscribe("greenhouse/action/approved",   qos=1)
    client.subscribe("greenhouse/ood/metrics",       qos=1)
    client.subscribe("greenhouse/supervisor/verdict", qos=1)
```

### `_on_message` — dispatch table

```python
TOPIC_MAP = {
    "greenhouse/telemetry":           (_handle_telemetry,  TelemetryPayload),
    "greenhouse/action/approved":     (_handle_action,     ActionPayload),
    "greenhouse/ood/metrics":         (_handle_ood,        OODMetrics),
    "greenhouse/supervisor/verdict":  (_handle_verdict,    SupervisorVerdict),
}

def _on_message(self, client, userdata, msg):
    handler, schema = TOPIC_MAP.get(msg.topic, (None, None))
    if handler is None:
        return
    try:
        payload = schema.model_validate_json(msg.payload)
        handler(self._ss, payload)
    except Exception as e:
        # Never crash the listener thread on bad data
        print(f"[Dashboard MQTT] Parse error on {msg.topic}: {e}")
```

### Individual handlers

```python
def _handle_telemetry(ss, p: TelemetryPayload):
    ss["steps"].append(p.step)
    ss["t_in"].append(p.t_in)
    ss["co2"].append(p.co2)
    ss["rh"].append(p.rh)
    ss["T_out"].append(p.T_out)
    ss["rad"].append(p.rad)

def _handle_action(ss, p: ActionPayload):
    ss["uBoil"].append(p.uBoil)
    ss["uCO2"].append(p.uCO2)
    ss["uThScr"].append(p.uThScr)
    ss["uVent"].append(p.uVent)
    ss["uLamp"].append(p.uLamp)
    ss["uBlScr"].append(p.uBlScr)

def _handle_ood(ss, p: OODMetrics):
    ss["mahal_dist"].append(p.mahalanobis_distance)
    ss["in_distribution"].append(p.in_distribution)
    ss["ood_threshold"] = p.threshold_used

def _handle_verdict(ss, p: SupervisorVerdict):
    status = {
        "APPROVE":  "🟢 SAFE",
        "OVERRIDE": "🟡 WARNING",
        "REJECT":   "🔴 ALARM",
    }.get(p.decision, "⚪ UNKNOWN")
    ss["agent_log"].appendleft({
        "step":      p.step,
        "status":    status,
        "decision":  p.decision,
        "reason":    p.reason,
        "confidence": p.confidence,
    })
```

---

## 5. Streamlit App (`dashboard/app.py`)

### 5.1 Startup and Listener Initialisation

The listener must be started exactly once per Streamlit session, not on every
script re-run. Use `st.session_state` to track whether it is already running.

```python
st.set_page_config(page_title="Greenhouse Control Dashboard", layout="wide")

# Initialise state on first run only
if "steps" not in st.session_state:
    for k, v in DEFAULT_STATE.items():
        st.session_state[k] = v
    listener = DashboardMQTTListener(
        host=MQTT_HOST, port=MQTT_PORT, session_state=st.session_state
    )
    listener.start()
    st.session_state["_listener"] = listener   # keep reference alive
```

### 5.2 Auto-Refresh

Streamlit does not re-render unless triggered by a user interaction. Use
`st_autorefresh` (from the `streamlit-autorefresh` package) to poll every N
seconds:

```python
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="dashboard_refresh")  # 2-second refresh
```

Alternatively, use `st.rerun()` inside a `time.sleep` loop in a background
thread, but `st_autorefresh` is simpler and officially recommended.

### 5.3 Layout

```
┌───────────────────────────────── HEADER ──────────────────────────────────────┐
│  🌱 Greenhouse Control — Live Dashboard   [MQTT: 🟢 Connected / 🔴 Offline]  │
│  Step: 4320  |  Elapsed: 18.0 h                                               │
└───────────────────────────────────────────────────────────────────────────────┘

┌─────── Column 1 (60%) ─────────────────┐  ┌────── Column 2 (40%) ────────────┐
│  TAB 1: Thermodynamics                 │  │  OOD Monitor                     │
│  TAB 2: Actuators                      │  │  Supervisor Log                  │
└────────────────────────────────────────┘  └──────────────────────────────────┘
```

### 5.4 Tab 1 — Thermodynamics

Three sub-charts stacked vertically, sharing the x-axis (step number):

```python
df = pd.DataFrame({
    "step": list(ss["steps"]),
    "t_in": list(ss["t_in"]),
    "co2":  list(ss["co2"]),
    "rh":   list(ss["rh"]),
    "T_out": list(ss["T_out"]),
})

# Temperature
fig_t = px.line(df, x="step", y=["t_in", "T_out"],
                labels={"value": "°C"}, title="Temperature")
fig_t.add_hline(y=20.0, line_dash="dash", annotation_text="Setpoint 20°C")
fig_t.add_hrect(y0=18, y1=22, fillcolor="green", opacity=0.05)

# CO2
fig_co2 = px.line(df, x="step", y="co2", title="CO₂ (ppm)")
fig_co2.add_hline(y=800, line_dash="dash", annotation_text="Setpoint 800 ppm")
fig_co2.add_hrect(y0=600, y1=1000, fillcolor="green", opacity=0.05)

# Humidity
fig_rh = px.line(df, x="step", y="rh", title="Relative Humidity (%)")
fig_rh.add_hline(y=85, line_color="red", line_dash="dot",
                 annotation_text="Max 85%")
```

### 5.5 Tab 2 — Actuators

Two rows of three charts (one per actuator). Each chart uses a filled area
(`px.area`) so chattering (rapid oscillation) is immediately visible.

```python
ACTUATORS = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]
LABELS    = ["Boiler", "CO₂ Inject", "Thermal Screen",
             "Ventilation", "Lamps", "Blackout Screen"]

cols = st.columns(3)
for i, (key, label) in enumerate(zip(ACTUATORS, LABELS)):
    with cols[i % 3]:
        fig = px.area(
            x=list(ss["steps"]), y=list(ss[key]),
            range_y=[0, 1], title=label,
            labels={"x": "step", "y": "signal [0–1]"}
        )
        st.plotly_chart(fig, use_container_width=True)
```

### 5.6 OOD Monitor

A line chart of Mahalanobis distance with a threshold band. When the metric
crosses the threshold, the chart turns red.

```python
df_ood = pd.DataFrame({
    "step":  list(ss["steps"]),
    "mahal": list(ss["mahal_dist"]),
})
threshold = ss["ood_threshold"]

fig_ood = px.line(df_ood, x="step", y="mahal",
                  title="OOD Mahalanobis Distance",
                  labels={"mahal": "Distance (σ)"})
fig_ood.add_hline(
    y=threshold, line_color="orange", line_dash="dash",
    annotation_text=f"Retraining Threshold ({threshold:.1f}σ)"
)
# Shade in-distribution zone
fig_ood.add_hrect(y0=0, y1=threshold, fillcolor="green", opacity=0.05)
# Shade OOD zone
fig_ood.add_hrect(y0=threshold, y1=threshold * 3,
                  fillcolor="red", opacity=0.05)

# Count OOD events in current window
n_ood = sum(1 for v in ss["in_distribution"] if not v)
st.metric("OOD Events in Window", n_ood,
          delta=None, delta_color="inverse")
st.plotly_chart(fig_ood, use_container_width=True)
```

### 5.7 Supervisor Log

A scrollable table of the last 50 Supervisor verdicts with colour-coded status.

```python
st.subheader("Supervisor Decisions")
if ss["agent_log"]:
    log_df = pd.DataFrame(list(ss["agent_log"]))
    st.dataframe(
        log_df[["step", "status", "decision", "confidence", "reason"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Waiting for Supervisor decisions...")
```

The `status` column contains the `🟢 SAFE` / `🟡 WARNING` / `🔴 ALARM` strings,
which Streamlit renders as emoji in the dataframe.

### 5.8 Header Status Bar

```python
st.title("🌱 Greenhouse Control — Live Dashboard")
c1, c2, c3, c4 = st.columns(4)
c1.metric("MQTT", "🟢 Connected" if ss["mqtt_connected"] else "🔴 Offline")
c2.metric("Current Step", ss["steps"][-1] if ss["steps"] else "—")
c3.metric("t_in", f"{ss['t_in'][-1]:.1f} °C" if ss["t_in"] else "—",
          delta=f"{ss['t_in'][-1] - 20.0:+.1f}" if ss["t_in"] else None)
c4.metric("CO₂",  f"{ss['co2'][-1]:.0f} ppm" if ss["co2"] else "—",
          delta=f"{ss['co2'][-1] - 800.0:+.0f}" if ss["co2"] else None)
```

---

## 6. Dependencies

Add to `requirements.txt` (dashboard section):

```
streamlit>=1.35
streamlit-autorefresh>=1.0
plotly>=5.20
paho-mqtt>=2.0
pandas>=2.0
```

---

## 7. Running the Dashboard

```bash
streamlit run dashboard/app.py -- --broker localhost --port 1883
```

Parse `sys.argv` extras with `argparse` *before* calling any `st.*` functions to
avoid conflicts with Streamlit's own argument parser.

---

## 8. Design Decisions and Constraints

| Decision | Rationale |
|---|---|
| No InfluxDB for MVP | Avoids operational overhead. `deque(maxlen=N)` gives a ~2-hour window at 15 min steps, sufficient for live monitoring. |
| Background thread for MQTT | Streamlit's main thread must not block. Paho's `loop_start()` handles all MQTT I/O in its own daemon thread. |
| Plotly over Altair/Matplotlib | Plotly supports `add_hline` / `add_hrect` natively, making setpoint bands trivial to add. |
| `st_autorefresh` at 2 s | 15-minute step period means new data arrives slowly. 2-second UI refresh is a good balance between responsiveness and CPU load. |
| Deque maxlen = 576 | 96 steps/day × 6 days = 576. Gives enough history to see multi-day trends without unbounded memory growth. |
| Decoupled from control core | Dashboard imports only schemas. The control system runs whether the dashboard is open or not. |
