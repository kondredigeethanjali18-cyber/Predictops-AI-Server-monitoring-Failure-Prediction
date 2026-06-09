from kafka_producer import send_metrics

test_data = {
    "cpu_usage_percent": 50,
    "memory_usage_percent": 60
}

send_metrics(test_data)