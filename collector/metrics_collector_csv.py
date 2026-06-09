import psutil
import time
import socket
import csv
import os
from datetime import datetime


CSV_FILE = "data/server_metrics.csv"


def measure_latency(host="8.8.8.8", port=53, timeout=2):
    start = time.time()
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        latency = round((time.time() - start) * 1000, 2)
    except Exception:
        latency = -1
    return latency


def collect_metrics():
    errors = 0

    try:
        cpu = psutil.cpu_percent(interval=1)
    except Exception:
        cpu = None
        errors += 1

    try:
        memory = psutil.virtual_memory()
    except Exception:
        memory = None
        errors += 1

    try:
        disk = psutil.disk_usage("/")
    except Exception:
        disk = None
        errors += 1

    try:
        net = psutil.net_io_counters()
    except Exception:
        net = None
        errors += 1

    latency = measure_latency()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_usage_percent": cpu,
        "memory_usage_percent": memory.percent if memory else None,
        "memory_used_mb": round(memory.used / (1024 * 1024), 2) if memory else None,
        "disk_usage_percent": disk.percent if disk else None,
        "bytes_sent": net.bytes_sent if net else None,
        "bytes_received": net.bytes_recv if net else None,
        "request_latency_ms": latency,
        "error_count": errors,
        "active_processes": len(psutil.pids())
    }


def write_to_csv(data):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)


if __name__ == "__main__":
    print("📡 Collecting server metrics & saving to CSV...")
    while True:
        metrics = collect_metrics()
        write_to_csv(metrics)
        print(metrics)
        time.sleep(3)