import json
import logging
import time

from kafka import KafkaConsumer

from Backend.database.mongodb import metrics_collection
from Backend.services.prediction_service import predict_metric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_consumer() -> KafkaConsumer:
    while True:
        try:
            consumer = KafkaConsumer(
                "cpu-metrics",
                bootstrap_servers="kafka:9092",
                auto_offset_reset="latest",
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            )
            logger.info("Kafka consumer connected")
            return consumer
        except Exception as exc:
            logger.warning(f"Waiting for Kafka: {exc}")
            time.sleep(5)


consumer = create_consumer()

if metrics_collection is None:
    logger.error("metrics_collection is not initialized. MongoDB connection failed.")
else:
    for message in consumer:
        metric = message.value

        try:
            metrics_collection.insert_one(metric)
            prediction = predict_metric(metric)
        except Exception as exc:
            logger.error(f"Error processing metric: {exc}")
            continue

        logger.info(f"Saved metric: {metric}")
        logger.info(f"Prediction: {prediction}")
