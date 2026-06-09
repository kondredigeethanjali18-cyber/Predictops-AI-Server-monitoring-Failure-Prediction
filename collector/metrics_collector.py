import psutil
from kafka_producer import send_metrics
import time
from datetime import datetime , timezone

while True:

    metrics = {
        "timestamp": datetime.utcnow().isoformat(),

        "cpu_usage_percent": psutil.cpu_percent(),

        "memory_usage_percent": psutil.virtual_memory().percent,

        "memory_used_mb":
            round(psutil.virtual_memory().used / 1024 / 1024, 2),

        "disk_usage_percent":
            psutil.disk_usage('/').percent,

        "network_sent_mb":
            round(psutil.net_io_counters().bytes_sent / 1024 / 1024, 2),

        "network_received_mb":
            round(psutil.net_io_counters().bytes_recv / 1024 / 1024, 2)
    }

    send_metrics(metrics)

    time.sleep(2)