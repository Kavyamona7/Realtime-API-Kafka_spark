import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, from_json, max, min, window
from pyspark.sql.types import DoubleType, StringType, StructType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints" / "crypto"

# Use repo-local Hadoop utilities on Windows so winutils/dll are found.
os.environ.setdefault("HADOOP_HOME", str(PROJECT_ROOT / "hadoop"))

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "raw_events")
KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1"
KAFKA_STARTING_OFFSETS = os.getenv("KAFKA_STARTING_OFFSETS", "latest")
KAFKA_FAIL_ON_DATA_LOSS = os.getenv("KAFKA_FAIL_ON_DATA_LOSS", "false")
CHECKPOINT_LOCATION = Path(os.getenv("CHECKPOINT_LOCATION", str(DEFAULT_CHECKPOINT_DIR))).as_posix()

spark = SparkSession.builder \
    .appName("CryptoStreaming") \
    .config("spark.sql.shuffle.partitions", "2") \
    .config("spark.sql.streaming.metricsEnabled", "false") \
    .config("spark.jars.packages", KAFKA_PACKAGE) \
    .getOrCreate()

schema = StructType() \
    .add("symbol", StringType()) \
    .add("price", DoubleType()) \
    .add("event_time", StringType())

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", KAFKA_STARTING_OFFSETS) \
    .option("failOnDataLoss", KAFKA_FAIL_ON_DATA_LOSS) \
    .load()

json_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

processed_df = json_df \
    .withColumn("event_time", col("event_time").cast("timestamp"))

aggregated = processed_df \
    .withWatermark("event_time", "2 minutes") \
    .groupBy(
        window(col("event_time"), "1 minute", "30 seconds"),
        col("symbol")
    ) \
    .agg(
        avg("price").alias("avg_price"),
        max("price").alias("max_price"),
        min("price").alias("min_price")
    )

query = aggregated.writeStream \
    .outputMode("update") \
    .format("console") \
    .option("truncate", False) \
    .option("checkpointLocation", CHECKPOINT_LOCATION) \
    .start()

query.awaitTermination()
