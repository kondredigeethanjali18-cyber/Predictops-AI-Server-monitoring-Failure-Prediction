from pymongo import MongoClient

uri = "mongodb+srv://Predictops_user:Geethanjali12345@clusterpredictop.iabajyw.mongodb.net/?appName=Clusterpredictop"

client = MongoClient(uri)

print(client.list_database_names())