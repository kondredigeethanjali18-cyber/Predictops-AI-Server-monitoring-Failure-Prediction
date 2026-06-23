from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

try:

    client = MongoClient(MONGODB_URI)

    client.admin.command("ping")

    db = client["predictops"]

    metrics_collection = db["metrics"]
    predictions_collection = db["predictions"]

    print("MongoDB Connected")

except Exception as e:

    print(f"MongoDB Connection Error: {e}")

    metrics_collection = None
    predictions_collection = None