from kafka import KafkaConsumer
import json
import time

from Backend.database.mongodb import metrics_collection
from Backend.services.prediction_service import predict_metric

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


for message in consumer:

    try:

        metric = message.value

        metrics_collection.insert_one(metric)

        prediction = predict_metric(metric)

        print("Saved Metric:", metric)
        print("Prediction:", prediction)

    except Exception as e:

        print(f"Error Processing Message: {e}")