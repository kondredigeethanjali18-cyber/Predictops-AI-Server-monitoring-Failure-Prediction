import pandas as pd

# Load data
df = pd.read_csv("data/server_metrics.csv")

# ----------------------------------
# Server Metadata
# ----------------------------------

servers = [
    ("SRV001", "web-server-01", "ap-south-1", "production"),
    ("SRV002", "api-server-01", "ap-south-1", "production"),
    ("SRV003", "database-server-01", "us-east-1", "production"),
    ("SRV004", "cache-server-01", "eu-west-1", "staging"),
    ("SRV005", "worker-server-01", "ap-south-1", "development")
]

df["server_id"] = ""
df["server_name"] = ""
df["region"] = ""
df["environment"] = ""

for i in range(len(df)):
    server = servers[i % len(servers)]

    df.loc[i, "server_id"] = server[0]
    df.loc[i, "server_name"] = server[1]
    df.loc[i, "region"] = server[2]
    df.loc[i, "environment"] = server[3]

# ----------------------------------
# Feature Engineering
# ----------------------------------

# Total network traffic
df["network_total"] = (
    df["bytes_sent"] +
    df["bytes_received"]
)

# CPU / Memory ratio
df["cpu_memory_ratio"] = (
    df["cpu_usage_percent"] /
    (df["memory_usage_percent"] + 1)
)

# CPU trend
df["cpu_change"] = (
    df["cpu_usage_percent"].diff()
)

# Memory trend
df["memory_change"] = (
    df["memory_usage_percent"].diff()
)

# Latency per process
df["latency_per_process"] = (
    df["request_latency_ms"] /
    (df["active_processes"] + 1)
)

# Replace NaN from diff()
df.fillna(0, inplace=True)

# ----------------------------------
# Temporary Anomaly Label
# ----------------------------------

df["anomaly"] = (
    (df["cpu_usage_percent"] > 90)
    |
    (df["memory_usage_percent"] > 90)
    |
    (df["error_count"] > 10)
).astype(int)

# Save output
output_path = "data/processed/feature_engineered_metrics.csv"

df.to_csv(output_path, index=False)

print("Feature engineering completed")
print("Saved:", output_path)
print("Rows:", len(df))