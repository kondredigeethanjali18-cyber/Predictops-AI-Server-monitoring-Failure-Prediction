import psutil
from kafka_producer import send_metrics
import time
from datetime import datetime, timezone
import random
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from data.servers import SERVERS

while True:

    for server in SERVERS:

        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent

        # Different behavior for each server
        if server["server_name"] == "db-server-01":
            cpu += random.randint(15, 30)

        elif server["server_name"] == "api-server-01":
            memory += random.randint(10, 20)

        elif server["server_name"] == "cache-server-01":
            cpu += random.randint(5, 15)

        metrics = {

            "server_id": server["server_id"],
            "server_name": server["server_name"],

            "timestamp":
                datetime.now(timezone.utc).isoformat(),

            "cpu_usage_percent":
                min(round(cpu, 2), 100),

            "memory_usage_percent":
                min(round(memory, 2), 100),

            "memory_used_mb":
                round(
                    psutil.virtual_memory().used /
                    1024 / 1024,
                    2
                ),

            "disk_usage_percent":
                psutil.disk_usage('/').percent,

            "network_sent_mb":
                round(
                    psutil.net_io_counters().bytes_sent /
                    1024 / 1024,
                    2
                ),

            "network_received_mb":
                round(
                    psutil.net_io_counters().bytes_recv /
                    1024 / 1024,
                    2
                )
        }

        send_metrics(metrics)

        print(
            f"Sent {server['server_name']} "
            f"CPU={metrics['cpu_usage_percent']} "
            f"MEM={metrics['memory_usage_percent']}"
        )

    time.sleep(5)