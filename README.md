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
<img width="1122" height="562" alt="image" src="https://github.com/user-attachments/assets/05c3c27b-89c7-48ec-bb4a-27d825f706ab" />

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
  <img width="1133" height="420" alt="newplot (2)" src="https://github.com/user-attachments/assets/3b4a9dea-8c90-4346-89d9-5ea43be20c01" />

- Real-time symbol trend chart
- Latest price snapshot chart
  <img width="652" height="420" alt="newplot (3)" src="https://github.com/user-attachments/assets/26b5b81c-903d-4a28-a21c-82628cda3798" />

- 3-minute symbol summary table
  <img width="1522" height="188" alt="image" src="https://github.com/user-attachments/assets/4b92dcfe-000e-4592-a69e-8c00a29c4216" />

- Live tape (time, symbol, partition, offset)
  <img width="1526" height="415" alt="image" src="https://github.com/user-attachments/assets/5ea39c95-27c6-46ca-b686-b47e2ba35de2" />

- Sidebar controls for refresh interval, topic, symbols, and memory window
  <img width="1600" height="724" alt="image" src="https://github.com/user-attachments/assets/a2392cbe-c6ae-46d2-bbc8-3dd472f26b48" />
  <img width="452" height="851" alt="image" src="https://github.com/user-attachments/assets/e9b3fa17-a62a-4f41-b7d3-45a7a526dda4" />


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
<img width="1210" height="200" alt="image" src="https://github.com/user-attachments/assets/6ebf388e-4ae2-4b2c-bb0e-a7ee3f6f401f" />

- Confirm Kafka is running: `docker ps`
- Confirm producer is running and logging `Sent: ...`
- Confirm dashboard topic is `raw_events` and bootstrap server is `localhost:9092`

### Spark job fails on Windows

- Confirm Java 17+ is installed and available in `PATH`
- Ensure bundled paths exist:
  - `spark-4.1.1-bin-hadoop3\bin\spark-submit.cmd`
  - `hadoop\bin`
