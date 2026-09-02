previous_cpu = {}
previous_memory = {}


def build_features(metric):

    global previous_cpu
    global previous_memory

    server_name = metric.get("server_name", "Unknown")
    cpu = float(metric.get("cpu_usage_percent", 35.0))
    memory = float(metric.get("memory_usage_percent", 50.0))
    disk = float(metric.get("disk_usage_percent", 50.0))

    prev_cpu = previous_cpu.get(server_name, cpu)
    prev_memory = previous_memory.get(server_name, memory)

    # Convert network throughput into bytes scale expected by ML model
    net_sent = float(metric.get("network_sent_mb", 90.0))
    net_recv = float(metric.get("network_received_mb", 95.0))
    network_total = net_sent + net_recv
    if network_total < 50000:
        # Values are in megabytes, convert to bytes scale (~1.8e8 bytes)
        network_total = network_total * 1024 * 1024

    request_latency_ms = float(metric.get(
        "request_latency_ms",
        120.0 if cpu < 80 else 220.0
    ))

    error_count = int(metric.get(
        "error_count",
        0 if cpu < 85 else 4
    ))

    active_processes = int(metric.get(
        "active_processes",
        343
    ))

    cpu_memory_ratio = cpu / max(memory, 1.0)
    cpu_change = cpu - prev_cpu
    memory_change = memory - prev_memory

    latency_per_process = (
        request_latency_ms /
        max(active_processes, 1)
    )

    previous_cpu[server_name] = cpu
    previous_memory[server_name] = memory

    memory_used_mb = float(metric.get("memory_used_mb", (memory / 100.0) * 16000.0))

    return {
        "cpu_usage_percent": cpu,
        "memory_usage_percent": memory,
        "memory_used_mb": memory_used_mb,
        "disk_usage_percent": disk,
        "network_total": network_total,
        "request_latency_ms": request_latency_ms,
        "error_count": error_count,
        "active_processes": active_processes,
        "cpu_memory_ratio": cpu_memory_ratio,
        "cpu_change": cpu_change,
        "memory_change": memory_change,
        "latency_per_process": latency_per_process
    }