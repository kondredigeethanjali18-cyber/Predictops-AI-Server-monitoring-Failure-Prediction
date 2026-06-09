from Backend.database.mongodb import predictions_collection

for doc in predictions_collection.find():
    print(doc)
    