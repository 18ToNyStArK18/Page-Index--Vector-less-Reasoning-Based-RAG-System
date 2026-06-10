import json
import os
from dbmanager import TreeDB

# 1. Initialize your DB manager (assuming the class is named TreeDBManager)
db_manager = TreeDB()

# 2. Define your local paths
json_path = "TheoryOfComputation.json"
pdf_path = "/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf" 

# 3. Read the JSON file shared by your friend
with open(json_path, "r") as f:
    shared_data = json.load(f)

# 4. Safely handle the formatting structure
# If your friend used mongoexport, the data will be wrapped inside a list/dict bundle
if isinstance(shared_data, list) and len(shared_data) > 0:
    # Unpack from mongoexport list format
    root_doc = shared_data[0]
    tree_dict = root_doc.get("tree", root_doc)
elif isinstance(shared_data, dict) and "tree" in shared_data:
    # Unpack if it's a direct MongoDB document export
    tree_dict = shared_data["tree"]
else:
    # It's already a clean raw tree dictionary
    tree_dict = shared_data

# 5. Execute your custom save_tree method gang!
db_manager.save_tree(pdf_path, tree_dict)
