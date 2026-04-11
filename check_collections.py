import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collections = client.list_collections()
print("现有集合列表：")
for col in collections:
    print(f"  - {col.name}")