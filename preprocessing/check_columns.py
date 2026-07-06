import pandas as pd

df = pd.read_csv("data/server_metrics.csv")

print(df.columns.tolist())