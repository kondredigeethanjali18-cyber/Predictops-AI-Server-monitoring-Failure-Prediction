import pandas as pd

df = pd.read_csv(
    "data/processed/feature_engineered_metrics.csv"
)

print(df["server_id"].unique())

print(
    "\nUnique Servers:",
    df["server_id"].nunique()
)