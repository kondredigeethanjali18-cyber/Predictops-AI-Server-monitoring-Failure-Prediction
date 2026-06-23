import logging
from os import getenv

from pymongo import MongoClient, ReadPreference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = getenv(
    "MONGO_URI",
    "mongodb://localhost:27017",
)
MONGO_DB = getenv("MONGO_DB", "predictops")
LOCAL_MONGO_URI = getenv("LOCAL_MONGO_URI", "mongodb://localhost:27017")


def create_mongo_client(uri: str) -> MongoClient:
    """Create a MongoClient instance using the provided URI."""
    connect_kwargs = {
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000,
        "appName": "PredictOpsAI",
    }

    if uri.startswith("mongodb+srv://"):
        connect_kwargs["tls"] = True
    else:
        connect_kwargs["tls"] = False

    return MongoClient(uri, **connect_kwargs)


def connect_mongo() -> MongoClient | None:
    """Try to connect to MongoDB using configured URIs and return the client."""
    try:
        client = create_mongo_client(MONGO_URI)
        client.admin.command("ping")
        logger.info("MongoDB connected using MONGO_URI")
        return client
    except Exception as exc:
        logger.warning(
            "MongoDB connection failed using MONGO_URI. "
            "Falling back to LOCAL_MONGO_URI if configured."
        )
        logger.warning(str(exc))

    if MONGO_URI.startswith("mongodb+srv://"):
        try:
            client = create_mongo_client(LOCAL_MONGO_URI)
            client.admin.command("ping")
            logger.info("MongoDB connected using LOCAL_MONGO_URI")
            return client
        except Exception as exc:
            logger.error("Local MongoDB fallback failed.")
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
    logger.error("MongoDB is not available. collections are set to None.")