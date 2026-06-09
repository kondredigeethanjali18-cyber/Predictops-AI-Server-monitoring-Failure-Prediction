from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["predictops"]

metrics_collection = db["metrics"]
predictions_collection = db["predictions"]

print("MongoDB Connected")