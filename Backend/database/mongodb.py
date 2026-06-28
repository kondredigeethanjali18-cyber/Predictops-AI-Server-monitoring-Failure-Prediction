import logging
from os import getenv
from time import sleep

from pymongo import MongoClient, ReadPreference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = getenv(
    "MONGO_URI",
    getenv("MONGODB_URI", "mongodb://localhost:27017"),
)
MONGO_DB = getenv("MONGO_DB", "predictops")
LOCAL_MONGO_URI = getenv("LOCAL_MONGO_URI", "mongodb://localhost:27017")
MONGO_CONNECT_RETRIES = int(getenv("MONGO_CONNECT_RETRIES", "6"))
MONGO_CONNECT_RETRY_DELAY = int(getenv("MONGO_CONNECT_RETRY_DELAY", "5"))


def create_mongo_client(uri: str) -> MongoClient:
    connect_kwargs = {
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000,
        "appName": "PredictOpsAI",
        "tls": uri.startswith("mongodb+srv://"),
    }

    return MongoClient(uri, **connect_kwargs)


def connect_mongo() -> MongoClient | None:
    for attempt in range(1, MONGO_CONNECT_RETRIES + 1):
        try:
            client = create_mongo_client(MONGO_URI)
            client.admin.command("ping")
            logger.info("MongoDB connected using MONGO_URI")
            return client
        except Exception as exc:
            logger.warning(
                "MongoDB connection failed using MONGO_URI "
                f"(attempt {attempt}/{MONGO_CONNECT_RETRIES})"
            )
            logger.warning(str(exc))

            if attempt < MONGO_CONNECT_RETRIES:
                sleep(MONGO_CONNECT_RETRY_DELAY)

    if MONGO_URI.startswith("mongodb+srv://"):
        try:
            client = create_mongo_client(LOCAL_MONGO_URI)
            client.admin.command("ping")
            logger.info("MongoDB connected using LOCAL_MONGO_URI")
            return client
        except Exception as exc:
            logger.error("Local MongoDB fallback failed")
            logger.error(str(exc))

    return None


client = connect_mongo()

if client is not None:
    db = client[MONGO_DB]
    metrics_collection = db["metrics"]
    predictions_collection = db.get_collection(
        "predictions",
        read_preference=ReadPreference.SECONDARY_PREFERRED,
    )
    logger.info("MongoDB collections initialized")
else:
    db = None
    metrics_collection = None
    predictions_collection = None
    logger.error("MongoDB is not available. Collections are set to None.")
