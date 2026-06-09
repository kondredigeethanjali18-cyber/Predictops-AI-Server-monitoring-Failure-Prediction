import pandas as pd
import numpy as np
import os

# Load raw dataset
df = pd.read_csv("data/server_metrics.csv")

print("Initial shape:", df.shape)

# ----------------------------
# 1️⃣ Handle missing values
# ----------------------------
df = df.dropna()

# ----------------------------
# 2️⃣ Fix invalid latency values
# ----------------------------
df = df[df["request_latency_ms"] >= 0]

# ----------------------------
# 3️⃣ Convert timestamp
# ----------------------------
df["timestamp"] = pd.to_datetime(df["timestamp"])

df["hour"] = df["timestamp"].dt.hour
df["day"] = df["timestamp"].dt.day
df["minute"] = df["timestamp"].dt.minute

df = df.drop(columns=["timestamp"])

# ----------------------------
# 4️⃣ Feature Engineering
# ----------------------------

# Network load
df["network_load"] = df["bytes_sent"] + df["bytes_received"]

# Resource pressure
df["resource_pressure"] = (
    df["cpu_usage_percent"] +
    df["memory_usage_percent"] +
    df["disk_usage_percent"]
) / 3

# ----------------------------
# 5️⃣ Remove raw network counters
# ----------------------------
df = df.drop(columns=["bytes_sent", "bytes_received"])

# ----------------------------
# 6️⃣ Outlier removal (simple)
# ----------------------------
df = df[df["cpu_usage_percent"] <= 100]
df = df[df["memory_usage_percent"] <= 100]
df = df[df["disk_usage_percent"] <= 100]

# ----------------------------
# Save cleaned dataset
# ----------------------------
os.makedirs("data/processed", exist_ok=True)
df.to_csv("data/processed/clean_server_metrics.csv", index=False)

print("Final shape:", df.shape)
print("✅ Preprocessing completed")

