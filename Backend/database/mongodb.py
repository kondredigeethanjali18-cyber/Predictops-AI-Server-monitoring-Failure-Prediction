from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://Predictops_user:Geethanjali12345@clusterpredictop.iabajyw.mongodb.net/?appName=Clusterpredictop"
)

db = client["predictops"]

metrics_collection = db["metrics"]
predictions_collection = db["predictions"]

print("MongoDB Connected")