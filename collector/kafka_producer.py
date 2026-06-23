
from kafka import KafkaProducer
import json
import time

producer = None

while producer is None:
    try:
        producer = KafkaProducer(
            bootstrap_servers='kafka:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Kafka Producer Connected")

    except Exception as e:
        print(f"Waiting for Kafka... {e}")
        time.sleep(5)

    


def send_metrics(metrics):

    try:

        if producer is None:
            raise Exception("Kafka Producer Not Available")

        producer.send("cpu-metrics", metrics)
        producer.flush()

        print("Sent:", metrics)

    except Exception as e:

        print(f"Failed to send metrics to Kafka: {e}")