from kafka import KafkaConsumer

consumer = KafkaConsumer(
    bootstrap_servers=["127.0.0.1:9092"],
    api_version=(3, 0, 0)
)

print("Connected")
print("Topics:", consumer.topics())     