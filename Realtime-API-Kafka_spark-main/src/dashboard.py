import json
import os
import time
from datetime import timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from kafka import KafkaConsumer


st.set_page_config(
    page_title="Crypto Stream Command Center",
    page_icon="📊",
    layout="wide",
)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

:root {
  --bg-start: #f2f8ff;
  --bg-end: #f9fbf2;
  --card: rgba(255, 255, 255, 0.86);
  --stroke: rgba(15, 23, 42, 0.1);
  --text: #0f172a;
  --muted: #475569;
  --primary: #0f766e;
  --accent: #f97316;
}

.stApp {
  background:
    radial-gradient(1200px 300px at 92% -10%, rgba(20, 184, 166, 0.15), transparent 52%),
    radial-gradient(1000px 260px at -10% 12%, rgba(249, 115, 22, 0.12), transparent 48%),
    linear-gradient(135deg, var(--bg-start), var(--bg-end));
  color: var(--text);
  font-family: "Manrope", "Segoe UI", sans-serif;
}

h1, h2, h3 {
  font-family: "Space Grotesk", "Segoe UI", sans-serif !important;
  letter-spacing: -0.02em;
}

[data-testid="stSidebar"] > div:first-child {
  background: linear-gradient(180deg, #fbfffe, #f6f9ff);
  border-right: 1px solid var(--stroke);
}

.hero {
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 1.1rem 1.2rem;
  background: var(--card);
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  margin-bottom: 1rem;
}

.hero-title {
  font-size: 1.55rem;
  font-weight: 800;
  line-height: 1.2;
}

.hero-sub {
  color: var(--muted);
  margin-top: 0.35rem;
}

.metric-card {
  border: 1px solid var(--stroke);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  background: var(--card);
  box-shadow: 0 7px 20px rgba(15, 23, 42, 0.05);
  min-height: 108px;
}

.metric-label {
  font-size: 0.82rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.metric-value {
  margin-top: 0.18rem;
  font-size: 1.58rem;
  font-weight: 800;
}

.metric-sub {
  margin-top: 0.22rem;
  color: var(--muted);
  font-size: 0.86rem;
}

div[data-testid="stPlotlyChart"] {
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: var(--card);
  box-shadow: 0 7px 24px rgba(15, 23, 42, 0.05);
  padding: 0.55rem;
}

div[data-testid="stDataFrame"] {
  border: 1px solid var(--stroke);
  border-radius: 14px;
  overflow: hidden;
}
</style>
    """,
    unsafe_allow_html=True,
)


DEFAULT_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DEFAULT_TOPIC = os.getenv("KAFKA_TOPIC", "raw_events")


@st.cache_resource(show_spinner=False)
def get_consumer(bootstrap_servers: str, topic: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=[item.strip() for item in bootstrap_servers.split(",") if item.strip()],
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=1000,
        request_timeout_ms=30000,
        api_version_auto_timeout_ms=30000,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )


def poll_events(consumer: KafkaConsumer, max_records: int, timeout_ms: int) -> list[dict]:
    rows: list[dict] = []
    batches = consumer.poll(timeout_ms=timeout_ms, max_records=max_records)
    for messages in batches.values():
        for message in messages:
            payload = message.value if isinstance(message.value, dict) else {}
            symbol = payload.get("symbol")
            price = payload.get("price")
            event_time = payload.get("event_time")
            rows.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "event_time": event_time,
                    "offset": message.offset,
                    "partition": message.partition,
                }
            )
    return rows


def normalize_events(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["symbol", "price", "event_time", "offset", "partition"])
    frame = pd.DataFrame(rows)
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame["event_time"] = pd.to_datetime(frame["event_time"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["symbol", "price", "event_time"])
    frame = frame.sort_values("event_time").reset_index(drop=True)
    return frame


def draw_metric(label: str, value: str, subtext: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.header("Control Panel")
    bootstrap_servers = st.text_input("Kafka bootstrap servers", value=DEFAULT_BOOTSTRAP)
    topic = st.text_input("Kafka topic", value=DEFAULT_TOPIC)
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh interval (seconds)", 2, 20, 4)
    max_records = st.slider("Records per refresh", 20, 500, 150, 10)
    history_limit = st.slider("Rows to keep in memory", 200, 5000, 1500, 100)
    manual_refresh = st.button("Refresh now", use_container_width=True)


if "events" not in st.session_state:
    st.session_state.events = pd.DataFrame(
        columns=["symbol", "price", "event_time", "offset", "partition"]
    )
if "source_key" not in st.session_state:
    st.session_state.source_key = ""

source_key = f"{bootstrap_servers}|{topic}"
if st.session_state.source_key != source_key:
    st.session_state.source_key = source_key
    st.session_state.events = st.session_state.events.iloc[0:0]


consumer_error = None
new_rows = []
try:
    consumer = get_consumer(bootstrap_servers, topic)
    new_rows = poll_events(consumer, max_records=max_records, timeout_ms=1200)
except Exception as exc:  # pragma: no cover - defensive path for runtime environment
    consumer_error = str(exc)


incoming = normalize_events(new_rows)
if not incoming.empty:
    merged = pd.concat([st.session_state.events, incoming], ignore_index=True)
    merged = merged.drop_duplicates(
        subset=["symbol", "event_time", "price", "offset", "partition"], keep="last"
    )
    merged = merged.sort_values("event_time").tail(history_limit).reset_index(drop=True)
    st.session_state.events = merged

events = st.session_state.events.copy()
symbols_available = sorted(events["symbol"].dropna().unique().tolist()) if not events.empty else []
selected_symbols = st.sidebar.multiselect(
    "Symbols",
    options=symbols_available,
    default=symbols_available,
)
if selected_symbols:
    events = events[events["symbol"].isin(selected_symbols)]


st.markdown(
    """
    <div class="hero">
      <div class="hero-title">Crypto Stream Command Center</div>
      <div class="hero-sub">Live Kafka consumer dashboard built with Streamlit, Plotly, and pandas.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if consumer_error:
    st.error(f"Kafka connection error: {consumer_error}")

total_events = len(events)
tracked_symbols = events["symbol"].nunique() if not events.empty else 0
last_event = events["event_time"].max() if not events.empty else None
last_event_text = (
    last_event.tz_convert(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if last_event is not None
    else "No data yet"
)
events_per_min = 0.0
if not events.empty:
    window_start = events["event_time"].max() - pd.Timedelta(minutes=1)
    events_per_min = float((events["event_time"] >= window_start).sum())

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
with metric_col_1:
    draw_metric("Status", "Live" if not consumer_error else "Degraded", f"Topic: {topic}")
with metric_col_2:
    draw_metric("Total Events", f"{total_events:,}", "Rows in dashboard memory")
with metric_col_3:
    draw_metric("Tracked Symbols", f"{tracked_symbols}", f"{events_per_min:.0f} events in last minute")
with metric_col_4:
    draw_metric("Last Event", last_event_text, f"Source: {bootstrap_servers}")

if events.empty:
    st.warning("No events available yet. Start `scripts/start_producer.ps1` and refresh.")
else:
    latest_snapshot = (
        events.sort_values("event_time").groupby("symbol", as_index=False).tail(1).sort_values("symbol")
    )
    trend_fig = px.line(
        events.sort_values("event_time"),
        x="event_time",
        y="price",
        color="symbol",
        markers=True,
        title="Live Price Trend",
        color_discrete_sequence=["#0f766e", "#0284c7", "#f97316", "#ef4444", "#22c55e"],
    )
    trend_fig.update_layout(
        margin=dict(l=20, r=20, t=56, b=18),
        height=420,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        legend_title_text="",
        xaxis_title="Event Time (UTC)",
        yaxis_title="Price",
    )

    snapshot_fig = px.bar(
        latest_snapshot,
        x="symbol",
        y="price",
        color="symbol",
        text_auto=".4f",
        title="Latest Price Snapshot",
        color_discrete_sequence=["#0f766e", "#0284c7", "#f97316", "#ef4444", "#22c55e"],
    )
    snapshot_fig.update_layout(
        margin=dict(l=20, r=20, t=56, b=18),
        height=420,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        showlegend=False,
        xaxis_title="Symbol",
        yaxis_title="Price",
    )

    chart_col_1, chart_col_2 = st.columns([1.9, 1.1])
    with chart_col_1:
        st.plotly_chart(trend_fig, use_container_width=True)
    with chart_col_2:
        st.plotly_chart(snapshot_fig, use_container_width=True)

    recent_window = events["event_time"].max() - pd.Timedelta(minutes=3)
    summary = (
        events[events["event_time"] >= recent_window]
        .groupby("symbol", as_index=False)["price"]
        .agg(avg_price="mean", max_price="max", min_price="min", points="count")
        .round(5)
        .sort_values("symbol")
    )
    st.subheader("3-Minute Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    tape = events.sort_values("event_time", ascending=False).head(40).copy()
    tape["event_time"] = tape["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    tape = tape[["event_time", "symbol", "price", "partition", "offset"]]
    st.subheader("Live Tape")
    st.dataframe(tape, use_container_width=True, hide_index=True)


if auto_refresh and not manual_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
