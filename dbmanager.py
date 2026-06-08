import hashlib
import os
from pymongo import MongoClient

class TreeDB:
    def __init__(self , db_url = "mongodb://localhost:27017/" , db_name = "rag_system"):
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]
        self.collection = self.db["pdf_trees"]
    
    def get_pdf_hash(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    
    def load_tree(self, file_path):
        hashed = self.get_pdf_hash(file_path)
        doc = self.collection.find_one({"_id": hashed})
        
        if doc:
            return doc
        else:
            return None
    
    def save_tree(self,file_path, treedict):
        hashed = self.get_pdf_hash(file_path)
        filename = os.path.basename(file_path)
        
        self.collection.update_one(
            {"_id" : hashed},
            {"$set": {
                "filename": filename,
                "tree": treedict
            }},
            upsert=True
        )
        print("[DB] Successfully saved fully summarized tree to MongoDB!")
        
        return
        
        