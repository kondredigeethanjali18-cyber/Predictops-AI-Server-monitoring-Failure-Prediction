import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, ReadPreference

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "predictops")
LOCAL_MONGO_URI = os.getenv("LOCAL_MONGO_URI", "mongodb://localhost:27017")

client = None
db = None
metrics_collection = None
predictions_collection = None


def connect_mongo() -> MongoClient | None:
    global client, db, metrics_collection, predictions_collection

    candidate_uris = [
        MONGO_URI,
        LOCAL_MONGO_URI,
        "mongodb://localhost:27017",
        "mongodb://127.0.0.1:27017"
    ]

    # Remove duplicates while preserving order
    seen = set()
    uris_to_try = []
    for u in candidate_uris:
        if u and u not in seen:
            seen.add(u)
            uris_to_try.append(u)

    for uri in uris_to_try:
        try:
            connect_kwargs = {
                "serverSelectionTimeoutMS": 2000,
                "connectTimeoutMS": 2000,
                "appName": "PredictOpsAI",
                "tls": uri.startswith("mongodb+srv://"),
            }
            c = MongoClient(uri, **connect_kwargs)
            c.admin.command("ping")
            logger.info(f"MongoDB connected successfully to {uri.split('@')[-1] if '@' in uri else uri}")
            client = c
            db = client[MONGO_DB]
            metrics_collection = db["metrics"]
            predictions_collection = db["predictions"]
            return client
        except Exception as exc:
            logger.warning(f"Connection to {uri.split('@')[-1] if '@' in uri else uri} failed: {exc}")

    logger.error("All MongoDB connection attempts failed.")
    return None


# Initialize on import
connect_mongo()


def get_db():
    global db
    if db is None:
        connect_mongo()
    return db


def get_metrics_collection():
    global metrics_collection
    if metrics_collection is None:
        connect_mongo()
    return metrics_collection


def get_predictions_collection():
    global predictions_collection
    if predictions_collection is None:
        connect_mongo()
    return predictions_collection
