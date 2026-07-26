import time
import random
import sys
import os
from datetime import datetime, timezone

# Ensure collector directory and project root are in sys.path
collector_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(collector_dir)
if collector_dir not in sys.path:
    sys.path.insert(0, collector_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from kafka_producer import send_metrics
from data.servers import SERVERS

print(f"[OK] Telemetry Collector started for fleet of {len(SERVERS)} servers with 8-second streaming interval.")

while True:
    try:
        incident_servers = {"SRV003", "SRV007", "SRV015", "SRV022"}

        for server in SERVERS:
            sname = server["server_name"]
            try:
                if sname in incident_servers:
                    # Active Anomaly Telemetry
                    cpu_usage = round(random.uniform(91.5, 98.4), 1)
                    memory_percent = round(random.uniform(86.0, 96.5), 1)
                    disk_usage = round(random.uniform(84.0, 93.5), 1)
                    latency = round(random.uniform(360.0, 680.0), 1)
                    active_procs = random.randint(344, 356)
                else:
                    # Healthy Baseline Telemetry
                    cpu_usage = round(random.uniform(22.0, 64.0), 1)
                    memory_percent = round(random.uniform(28.0, 68.0), 1)
                    disk_usage = round(random.uniform(25.0, 65.0), 1)
                    latency = round(random.uniform(35.0, 85.0), 1)
                    active_procs = random.randint(335, 345)

                metrics = {
                    "server_id": server["server_id"],
                    "server_name": sname,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_percent": memory_percent,
                    "memory_used_mb": round((memory_percent / 100.0) * 16000.0, 2),
                    "disk_usage_percent": disk_usage,
                    "network_sent_mb": round(random.uniform(70, 160), 2),
                    "network_received_mb": round(random.uniform(70, 160), 2),
                    "request_latency_ms": latency,
                    "active_processes": active_procs
                }

                send_metrics(metrics)

                print(
                    f"Emitted {sname} | "
                    f"CPU={metrics['cpu_usage_percent']}% | "
                    f"MEM={metrics['memory_usage_percent']}% | "
                    f"DISK={metrics['disk_usage_percent']}%"
                )

            except Exception as e:
                print(f"Error processing {sname}: {e}")

        print("[INFO] Completed 8-second telemetry cycle. Sleeping 8 seconds...")
        time.sleep(8)

    except Exception as e:
        print(f"Metrics Collector Error: {e}")
        time.sleep(8)