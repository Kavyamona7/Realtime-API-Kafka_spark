# Real-Time Crypto Streaming Pipeline (Kafka + Spark + Streamlit)

This project streams live crypto prices from Binance into Kafka, processes the stream with Spark Structured Streaming, and visualizes results in a Streamlit dashboard.

## Architecture

- `src/api_producer.py`: Polls Binance (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`) every 5 seconds and publishes to Kafka topic `raw_events`.
- `src/streaming_app.py`: Reads Kafka stream and computes 1-minute window aggregates (avg/max/min) with watermarking.
- `src/dashboard.py`: Reads Kafka directly for a live UI with KPIs, charts, and event tape.
- `docker/docker-compose.yml`: Local Zookeeper + Kafka.
- `scripts/start_producer.ps1`: Starts producer via repo `venv`.
- `scripts/start_streaming.ps1`: Starts Spark job using bundled Spark + Hadoop helpers.
- `scripts/start_dashboard.ps1`: Starts Streamlit on port `8501`.

## Prerequisites

- Windows + PowerShell
- Python 3.13
- Java 17+ (`java -version`)
- Docker Desktop

## Quick Start

Run from repo root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start infrastructure:

```powershell
docker compose -f .\docker\docker-compose.yml up -d
```

Start apps in 3 separate terminals:

```powershell
.\scripts\start_producer.ps1
```

```powershell
.\scripts\start_streaming.ps1
```

```powershell
.\scripts\start_dashboard.ps1
```

Open dashboard: `http://localhost:8501`

## Environment Variables

`src/streaming_app.py`:

- `KAFKA_BOOTSTRAP_SERVERS` (default: `localhost:9092`)
- `KAFKA_TOPIC` (default: `raw_events`)
- `KAFKA_STARTING_OFFSETS` (default: `latest`)
- `KAFKA_FAIL_ON_DATA_LOSS` (default: `false`)
- `CHECKPOINT_LOCATION` (default in code: `checkpoints/crypto`)

Note: `scripts/start_streaming.ps1` sets `CHECKPOINT_LOCATION` to a fresh run folder under `checkpoints/crypto_runtime/run_YYYYMMDD_HHMMSS` by default.
Set `CHECKPOINT_MODE=reuse` if you want to reuse `checkpoints/crypto_runtime` instead.

`src/dashboard.py`:

- `KAFKA_BOOTSTRAP_SERVERS` (default: `localhost:9092`)
- `KAFKA_TOPIC` (default: `raw_events`)

## Dashboard Features

- Live Kafka consumption from `raw_events`
- Real-time symbol trend chart
- Latest price snapshot chart
- 3-minute symbol summary table
- Live tape (time, symbol, partition, offset)
- Sidebar controls for refresh interval, topic, symbols, and memory window

## Stop

- Stop producer/streaming/dashboard with `Ctrl + C`
- Stop Kafka/Zookeeper:

```powershell
docker compose -f .\docker\docker-compose.yml down
```

## Troubleshooting

### `No module named streamlit`

Your `venv` is missing dependencies. Install using the same interpreter used by scripts:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify:

```powershell
.\venv\Scripts\python.exe -m streamlit --version
```

### Dashboard opens but shows no data

- Confirm Kafka is running: `docker ps`
- Confirm producer is running and logging `Sent: ...`
- Confirm dashboard topic is `raw_events` and bootstrap server is `localhost:9092`

### Spark job fails on Windows

- Confirm Java 17+ is installed and available in `PATH`
- Ensure bundled paths exist:
  - `spark-4.1.1-bin-hadoop3\bin\spark-submit.cmd`
  - `hadoop\bin`
