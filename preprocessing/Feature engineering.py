import pandas as pd
import numpy as np

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

# Generate Synthetic Records

# ----------------------------------

synthetic_rows = []

for _ in range(1000):
  row = df.sample(1).iloc[0].copy()
  row["cpu_usage_percent"] += np.random.randint(-5, 6)
  row["memory_usage_percent"] += np.random.randint(-5, 6)
  row["disk_usage_percent"] += np.random.randint(-2, 3)
  row["bytes_sent"] += np.random.uniform(-50, 50)
  row["bytes_received"] += np.random.uniform(-50, 50)
  row["request_latency_ms"] += np.random.randint(-50, 51)
  synthetic_rows.append(row)
  synthetic_df = pd.DataFrame(synthetic_rows)

df = pd.concat(
[df, synthetic_df],
ignore_index=True
)

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

df = df.sort_values(by=["server_name"])
df["cpu_change"] = df.groupby("server_name")["cpu_usage_percent"].diff().fillna(0)

# Memory trend

df["memory_change"] = df.groupby("server_name")["memory_usage_percent"].diff().fillna(0)

# Latency per process

df["latency_per_process"] = (
df["request_latency_ms"] /
(df["active_processes"] + 1)
)

# Replace NaN values

df.fillna(0, inplace=True)

# ----------------------------------

# Improved Anomaly Label

# ----------------------------------

df["anomaly"] = (
    (
        (df["cpu_usage_percent"] > 85)
        &
        (df["memory_usage_percent"] > 75)
    )
    |
    (
        (df["request_latency_ms"] > 600)
        &
        (df["error_count"] > 5)
    )
    |
    (
        (df["disk_usage_percent"] > 90)
    )
).astype(int)

# ----------------------------------

# Save Dataset

# ----------------------------------

output_path = "data/processed/feature_engineered_metrics.csv"

df.to_csv(output_path, index=False)

print("Feature engineering completed")
print("Saved:", output_path)
print("Rows:", len(df))
print("\nAnomaly Distribution:")
print(df["anomaly"].value_counts())
