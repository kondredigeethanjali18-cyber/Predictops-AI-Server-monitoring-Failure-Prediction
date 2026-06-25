<<<<<<< HEAD
"""
Kafka Producer Module

This module is responsible for producing server metrics to a Kafka topic.
It handles the connection to a Kafka broker and sends serialized metrics data.
"""
=======
>>>>>>> e7ddcb323f78f0b35dd97a8b034311ba89863464

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

    

<<<<<<< HEAD
# Initialize the Kafka Producer
# Connects to local Kafka broker on port 9092
# Uses JSON serialization for message values
from kafka import KafkaProducer
import json
import time

producer = None

while producer is None:
    try:
        producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        print("Connected to Kafka")
    except Exception as e:
        print("Waiting for Kafka...", e)
        time.sleep(5)

def send_metrics(metrics):
    """
    Send metrics data to the 'cpu-metrics' Kafka topic.
    
    Args:
        metrics (dict): A dictionary containing the metrics data to be sent.
                       Typically includes CPU, memory, disk, and network metrics.
    
    Returns:
        None
    
    Side Effects:
        - Sends message to Kafka topic "cpu-metrics"
        - Flushes the producer buffer to ensure message delivery
        - Prints confirmation message to console
    """
    # Send metrics to the "cpu-metrics" topic
    producer.send("cpu-metrics", metrics)
    
    # Flush the producer buffer to ensure all messages are sent
    producer.flush()
    
    # Log confirmation of sent metrics
    print("Sent:", metrics)
=======

def send_metrics(metrics):

    try:

        if producer is None:
            raise Exception("Kafka Producer Not Available")

        producer.send("cpu-metrics", metrics)
        producer.flush()

        print("Sent:", metrics)

    except Exception as e:

        print(f"Failed to send metrics to Kafka: {e}")
>>>>>>> e7ddcb323f78f0b35dd97a8b034311ba89863464
