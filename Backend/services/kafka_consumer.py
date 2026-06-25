import json
<<<<<<< HEAD
import logging

from kafka import KafkaConsumer
=======
import time
>>>>>>> e7ddcb323f78f0b35dd97a8b034311ba89863464

from Backend.database.mongodb import metrics_collection
from Backend.services.prediction_service import predict_metric

<<<<<<< HEAD
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

consumer = KafkaConsumer(
    "cpu-metrics",
    bootstrap_servers="kafka:9092",
    auto_offset_reset="latest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

logger.info("Consumer started...")
=======
consumer = None

while consumer is None:

    try:

        consumer = KafkaConsumer(
            "cpu-metrics",
            bootstrap_servers="kafka:9092",
            auto_offset_reset="latest",
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )

        print("Kafka Consumer Connected")

    except Exception as e:

        print(f"Waiting for Kafka... {e}")
        time.sleep(5)

>>>>>>> e7ddcb323f78f0b35dd97a8b034311ba89863464

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

<<<<<<< HEAD
        prediction = predict_metric(metric)

        logger.info(f"Saved Metric: {metric}")
        logger.info(f"Prediction: {prediction}")
=======
    try:

        metric = message.value

        metrics_collection.insert_one(metric)

        prediction = predict_metric(metric)

        print("Saved Metric:", metric)
        print("Prediction:", prediction)

    except Exception as e:

        print(f"Error Processing Message: {e}")
>>>>>>> e7ddcb323f78f0b35dd97a8b034311ba89863464
