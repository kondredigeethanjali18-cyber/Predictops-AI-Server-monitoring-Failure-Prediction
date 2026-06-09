previous_cpu = 0
previous_memory = 0


def build_features(metric):

    global previous_cpu
    global previous_memory

    cpu = metric["cpu_usage_percent"]
    memory = metric["memory_usage_percent"]

    network_total = (
        metric["network_sent_mb"]
        + metric["network_received_mb"]
    )

    request_latency_ms = metric.get(
        "request_latency_ms",
        50
    )

    error_count = metric.get(
        "error_count",
        0
    )

    active_processes = metric.get(
        "active_processes",
        100
    )

    cpu_memory_ratio = cpu / max(memory, 1)

    cpu_change = cpu - previous_cpu

    memory_change = memory - previous_memory

    latency_per_process = (
        request_latency_ms /
        max(active_processes, 1)
    )

    previous_cpu = cpu
    previous_memory = memory

    return {
        "cpu_usage_percent": cpu,
        "memory_usage_percent": memory,
        "memory_used_mb": metric["memory_used_mb"],
        "disk_usage_percent": metric["disk_usage_percent"],
        "network_total": network_total,
        "request_latency_ms": request_latency_ms,
        "error_count": error_count,
        "active_processes": active_processes,
        "cpu_memory_ratio": cpu_memory_ratio,
        "cpu_change": cpu_change,
        "memory_change": memory_change,
        "latency_per_process": latency_per_process
    }