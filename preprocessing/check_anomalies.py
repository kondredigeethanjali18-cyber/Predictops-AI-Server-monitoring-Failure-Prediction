import pandas as pd

df = pd.read_csv(
    "data/processed/feature_engineered_metrics.csv"
)

print("Total Rows:", len(df))

print(
    "Anomaly Rows:",
    df["anomaly"].sum()
)

print(
    "Normal Rows:",
    (df["anomaly"] == 0).sum()
)