from pymongo import MongoClient
from os import getenv

uri = getenv("uri")

client = MongoClient(uri)

print(client.list_database_names())