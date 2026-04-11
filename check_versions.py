import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("physics_corpus")

# 获取所有元数据
all_data = collection.get(include=["metadatas"])
versions = set()
for meta in all_data['metadatas']:
    versions.add(meta.get('version'))
print("数据库中存在的版本：", versions)