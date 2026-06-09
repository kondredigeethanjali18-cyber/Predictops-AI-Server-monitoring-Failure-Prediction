from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_metrics(metrics):
    producer.send("cpu-metrics", metrics)
    producer.flush()
    print("Sent:", metrics)