import json
import logging
import os
import time

try:
    from kafka import KafkaConsumer
except ImportError:
    KafkaConsumer = None

from Backend.database.mongodb import get_metrics_collection
from Backend.services.prediction_service import predict_metric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092,localhost:9092").split(",")
consumer = None

if KafkaConsumer is not None:
    for attempt in range(1, 31):
        for server in kafka_servers:
            server = server.strip()
            if not server:
                continue
            try:
                consumer = KafkaConsumer(
                    "cpu-metrics",
                    bootstrap_servers=[server],
                    auto_offset_reset="latest",
                    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                    request_timeout_ms=3000
                )
                logger.info(f"Kafka Consumer connected successfully to {server} on topic 'cpu-metrics'")
                break
            except Exception as e:
                pass
        if consumer is not None:
            break
        logger.info(f"Waiting for Kafka broker ({attempt}/30)...")
        time.sleep(3)

if consumer is None:
    logger.warning("Kafka Consumer could not connect to broker. Exiting gracefully.")
    exit(0)

logger.info("Kafka Consumer is listening for live telemetry stream...")

for message in consumer:
    try:
        metric = message.value
        col = get_metrics_collection()
        if col is not None:
            col.insert_one(dict(metric))
        prediction = predict_metric(metric)
        logger.info(f"Processed metric for {metric.get('server_name')} -> {prediction.get('prediction')} ({prediction.get('confidence')}%)")
    except Exception as exc:
        logger.error(f"Error processing consumed metric: {exc}")