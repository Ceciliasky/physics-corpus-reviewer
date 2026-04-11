import json
import re
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm  # 可选，用于显示进度条

# ====== 配置 ======
DATA_JSON = Path("./enhanced_data.json")   # 优先使用 JSON
CLEANED_MD_DIR = Path("./cleaned_md")      # 备选：直接读 md 文件
CHROMA_DB_PATH = "./chroma_db"             # 向量数据库保存路径

# 选择嵌入模型（中文友好，轻量）
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

def split_into_paragraphs(text, max_len=500):
    """
    将文本按段落切分，并进一步切分过长的段落。
    - 首先按空行分割成段落
    - 如果段落长度超过 max_len，再按句子切分（简单按句号、问号、感叹号）
    """
    if not text:
        return []
    # 按空行分割（保留原有段落结构）
    raw_paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_len:
            chunks.append(para)
        else:
            # 过长段落按句子分割（保留标点）
            sentences = re.split(r'(?<=[。！？；])', para)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) <= max_len:
                    current += sent
                else:
                    if current:
                        chunks.append(current.strip())
                    current = sent
            if current:
                chunks.append(current.strip())
    return chunks

def main():
    # 1. 加载数据
    records = []
    if DATA_JSON.exists():
        with open(DATA_JSON, 'r', encoding='utf-8') as f:
            records = json.load(f)
        print(f"从 JSON 加载了 {len(records)} 个章节")
    elif CLEANED_MD_DIR.exists():
        # 如果 JSON 不存在，从 md 文件读取（需要解析文件名元数据）
        # 这里假设你已经有了 enhanced_data.json，所以先不实现，如有需要可以补充
        print("未找到 enhanced_data.json，请先运行 export_to_json.py 生成")
        return
    else:
        print("没有找到数据源")
        return

    # 2. 初始化 Chroma 客户端（持久化到本地目录）
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    # 创建或获取集合（collection）
    collection_name = "physics_corpus"
    # 如果已存在，可以选择删除重新创建（为了干净，先删除）
    try:
        client.delete_collection(collection_name)
        print(f"已删除旧集合 {collection_name}")
    except:
        pass
    # 使用 sentence-transformers 嵌入函数
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
    )

    # 3. 切分段落并添加
    all_chunks = []
    all_metadatas = []
    all_ids = []
    chunk_id = 0
    for rec in tqdm(records, desc="处理章节"):
        content = rec.get("content", "")
        if not content:
            continue
        chunks = split_into_paragraphs(content)
        for chunk in chunks:
            # 元数据：保留版本、年级等，并记录段落原文
            metadata = {
                "version": rec["version"],
                "grade": rec["grade"],
                "volume": rec["volume"],
                "chapter_number": rec["chapter_number"],
                "chapter_name": rec["chapter_name"],
                "concepts": ",".join(rec.get("concepts", []))  # 转为字符串
            }
            all_metadatas.append(metadata)
            all_chunks.append(chunk)
            all_ids.append(f"chunk_{chunk_id}")
            chunk_id += 1

    # 分批添加（Chroma 有默认限制，但这里数据量不大，可直接添加）
    # 注意：添加前确保嵌入函数已设置
    collection.add(
        documents=all_chunks,
        metadatas=all_metadatas,
        ids=all_ids
    )
    print(f"成功添加 {len(all_chunks)} 个段落，集合大小: {collection.count()}")

    # 4. 简单测试检索
    print("\n测试检索：查询 '力的作用效果'")
    results = collection.query(query_texts=["力的作用效果"], n_results=3)
    for i, doc in enumerate(results['documents'][0]):
        print(f"结果 {i+1}: {doc[:100]}... (来自 {results['metadatas'][0][i]['version']} {results['metadatas'][0][i]['chapter_name']})")

if __name__ == "__main__":
    main()