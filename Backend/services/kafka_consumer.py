from kafka import KafkaConsumer
import json

from Backend.database.mongodb import metrics_collection

consumer = KafkaConsumer(
    "cpu-metrics",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="latest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

print("Consumer Started...")

for message in consumer:

    metric = message.value

    metrics_collection.insert_one(metric)

    print("Saved to MongoDB:", metric)