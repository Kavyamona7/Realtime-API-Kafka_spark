import json
import time
import requests
from kafka import KafkaProducer
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BASE_URL = "https://api.binance.com/api/v3/ticker/price"

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=3
)

def fetch_price(symbol):
    try:
        response = requests.get(BASE_URL, params={"symbol": symbol}, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching {symbol}: {e}")
        return None

while True:
    for symbol in SYMBOLS:
        data = fetch_price(symbol)

        if data:
            event = {
                "symbol": data["symbol"],
                "price": float(data["price"]),
                "event_time": datetime.utcnow().isoformat()
            }

            producer.send("raw_events", event)
            logging.info(f"Sent: {event}")

    time.sleep(5)
