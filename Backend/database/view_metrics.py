from Backend.database.mongodb import metrics_collection

for doc in metrics_collection.find():
    print(doc)