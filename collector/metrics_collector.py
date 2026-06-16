import time
import random
import sys
import os

from datetime import datetime, timezone

from kafka_producer import send_metrics

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from data.servers import SERVERS


while True:

    try:

        for server in SERVERS:

            try:

                # Base metrics
                cpu_usage = round(random.uniform(10, 100), 1)
                memory_percent = round(random.uniform(20, 95), 1)
                disk_usage = round(random.uniform(10, 95), 1)

                # Server-specific behavior
                if server["server_name"] == "db-server-01":

                    cpu_usage += random.randint(15, 30)
                    disk_usage += random.randint(10, 20)

                elif server["server_name"] == "AP-server-01":

                    memory_percent += random.randint(10, 20)

                elif server["server_name"] == "cache-server-01":

                    cpu_usage += random.randint(5, 15)

                # Keep values within 100%
                cpu_usage = min(cpu_usage, 100)
                memory_percent = min(memory_percent, 100)
                disk_usage = min(disk_usage, 100)

                metrics = {

                    "server_id":
                        server["server_id"],

                    "server_name":
                        server["server_name"],

                    "timestamp":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),

                    "cpu_usage_percent":
                        round(cpu_usage, 2),

                    "memory_usage_percent":
                        round(memory_percent, 2),

                    "memory_used_mb":
                        round(
                            random.uniform(
                                1000,
                                16000
                            ),
                            2
                        ),

                    "disk_usage_percent":
                        round(disk_usage, 2),

                    "network_sent_mb":
                        round(
                            random.uniform(
                                10,
                                1000
                            ),
                            2
                        ),

                    "network_received_mb":
                        round(
                            random.uniform(
                                10,
                                1000
                            ),
                            2
                        )
                }

                send_metrics(metrics)

                print(
                    f"Sent {server['server_name']} | "
                    f"CPU={metrics['cpu_usage_percent']}% | "
                    f"MEM={metrics['memory_usage_percent']}% | "
                    f"DISK={metrics['disk_usage_percent']}%"
                )

            except Exception as e:

                print(
                    f"Error processing "
                    f"{server['server_name']}: {e}"
                )

        time.sleep(5)

    except Exception as e:

        print(
            f"Metrics Collector Error: {e}"
        )

        time.sleep(5)