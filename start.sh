#!/bin/bash

python -m Backend.services.kafka_consumer &
python collector/metrics_collector.py &
#!/bin/sh

uvicorn Backend.main:app --host 0.0.0.0 --port 8000
