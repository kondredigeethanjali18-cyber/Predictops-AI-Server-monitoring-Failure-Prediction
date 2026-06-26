import json
import time

from kafka import KafkaProducer

producer = None

while producer is None:
    try:
        producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print("Kafka Producer Connected")
    except Exception as exc:
        print(f"Waiting for Kafka... {exc}")
        time.sleep(5)


def send_metrics(metrics):
    try:
        producer.send("cpu-metrics", metrics)
        producer.flush()
        print("Sent:", metrics)
    except Exception as exc:
        print(f"Failed to send metrics to Kafka: {exc}")
