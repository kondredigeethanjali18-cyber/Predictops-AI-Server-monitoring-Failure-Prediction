import json
import logging

from kafka import KafkaConsumer

from Backend.database.mongodb import metrics_collection
from Backend.services.prediction_service import predict_metric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

consumer = KafkaConsumer(
    "cpu-metrics",
    bootstrap_servers="kafka:9092",
    auto_offset_reset="latest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

logger.info("Consumer started...")

if metrics_collection is None:
    logger.error("metrics_collection is not initialized. MongoDB connection failed.")
else:
    for message in consumer:
        metric = message.value
        try:
            metrics_collection.insert_one(metric)
        except Exception as exc:
            logger.error(f"Failed to save metric to MongoDB: {exc}")
            continue

        prediction = predict_metric(metric)

        logger.info(f"Saved Metric: {metric}")
        logger.info(f"Prediction: {prediction}")