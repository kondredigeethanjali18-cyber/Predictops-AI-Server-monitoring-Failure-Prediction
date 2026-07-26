import json
import time
import os
import sys
import socket

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None

producer = None

def is_kafka_reachable(host, port, timeout=0.5):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092,kafka:9092,127.0.0.1:9092").split(",")

if KafkaProducer is not None:
    for server in kafka_servers:
        server = server.strip()
        if not server:
            continue
        try:
            host, port = server.split(":")
        except ValueError:
            host, port = server, 9092

        if is_kafka_reachable(host, port):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=server,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    request_timeout_ms=2000,
                    max_block_ms=2000
                )
                print(f"[OK] Connected to Kafka Broker at {server}")
                break
            except Exception:
                producer = None

if producer is None:
    print("[INFO] Kafka broker not reachable. Using direct database telemetry ingestion fallback.")


def send_metrics(metrics):
    global producer
    if producer is not None:
        try:
            producer.send("cpu-metrics", metrics)
            producer.flush()
            return
        except Exception as exc:
            print(f"[WARN] Failed to send to Kafka ({exc}). Falling back to direct database ingestion.")

    # Direct database ingestion fallback
    try:
        from Backend.database.mongodb import metrics_collection
        from Backend.services.prediction_service import predict_metric

        if metrics_collection is not None:
            metrics_collection.insert_one(dict(metrics))
            predict_metric(metrics)
    except Exception as e:
        print(f"[ERROR] Direct ingestion error: {e}")
