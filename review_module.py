import os
import json
import jieba
from pathlib import Path
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from langchain_deepseek import ChatDeepSeek
from langchain.prompts import PromptTemplate

# ================== 1. 加载配置 ==================
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

# ================== 2. 加载标准术语词典 ==================
TERMS_FILE = Path("physics_terms.txt")
standard_terms = set()
if TERMS_FILE.exists():
    with open(TERMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            term = line.strip()
            if term:
                standard_terms.add(term)
else:
    print("警告：未找到 physics_terms.txt，术语检查功能将不可用。")

# ================== 3. 从向量数据库加载段落（文本+元数据）==================
def load_chunks_from_chroma():
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection("physics_corpus")
    all_data = collection.get(include=["documents", "metadatas"])
    chunks = []
    for doc, meta in zip(all_data['documents'], all_data['metadatas']):
        chunks.append({
            "text": doc,
            "version": meta.get('version', 'unknown'),
            "chapter_name": meta.get('chapter_name', ''),
            "chapter_number": meta.get('chapter_number', 0)
        })
    return chunks

print("正在从向量数据库加载段落...")
chunks = load_chunks_from_chroma()
print(f"已加载 {len(chunks)} 个段落。")

# ================== 4. 构建 BM25 检索器 ==================
print("正在构建 BM25 索引（首次运行会分词，请稍候）...")
tokenized_chunks = []
for chunk in chunks:
    tokens = list(jieba.cut(chunk["text"]))
    tokenized_chunks.append(tokens)
bm25 = BM25Okapi(tokenized_chunks)
print("BM25 索引构建完成。")

def bm25_retrieve(query: str, top_k: int = 200):
    query_tokens = list(jieba.cut(query))
    scores = bm25.get_scores(query_tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = []
    for idx in top_indices:
        results.append({
            "text": chunks[idx]["text"],
            "version": chunks[idx]["version"],
            "chapter_name": chunks[idx]["chapter_name"],
            "score": scores[idx]
        })
    return results

def retrieve_diverse_results(query: str, top_k_per_version: int = 2, max_results: int = 15):
    raw = bm25_retrieve(query, top_k=200)
    version_best = {}
    for res in raw:
        ver = res["version"]
        if ver not in version_best:
            version_best[ver] = []
        version_best[ver].append(res)
    for ver in version_best:
        version_best[ver].sort(key=lambda x: x["score"], reverse=True)
        version_best[ver] = version_best[ver][:top_k_per_version]
    final = []
    for items in version_best.values():
        final.extend(items)
    final.sort(key=lambda x: x["score"], reverse=True)
    return final[:max_results]

# ================== 5. 初始化 DeepSeek 模型 ==================
llm = ChatDeepSeek(model="deepseek-chat", temperature=0, api_key=DEEPSEEK_API_KEY)

# ================== 6. 知识审校提示词 ==================
KNOWLEDGE_PROMPT = PromptTemplate(
    template="""
你是一位初中物理教材审校专家。请完成以下两个任务：

### 任务一：审校待审文本
判断待审文本是否存在知识性错误、表述不严谨或与课程标准/主流教材不一致之处。

待审文本：{question}

### 任务二：对比不同版本教材的表述差异
根据提供的参考语料，总结不同版本教材对同一知识点的表述差异，以表格形式输出。

参考语料（来自不同版本）：
{context}

### 输出要求（请严格遵守以下格式，每项单独一行，不要挤在一起）：

**审校结果**

- **问题类型：** [知识性错误/术语不规范/逻辑矛盾/表述不严谨]
- **错误描述：** ...
- **修改建议：** ...
- **参考来源：** （版本、章节等）

**版本对比表**

| 版本 | 核心表述 | 补充说明 |
|------|----------|----------|
| 人教版 | ... | ... |
| 北师大版 | ... | ... |
| 沪教版 | ... | ... |
| 苏教版 | ... | ... |

如果待审文本正确且无任何问题，则只输出“✅ 正确”，但仍需输出**版本对比表**。

注意：不要使用任何 HTML 标签（如 <br>）。
""",
    input_variables=["question", "context"]
)

# ================== 7. 术语检查提示词 ==================
TERM_PROMPT = PromptTemplate(
    template="""
你是物理术语专家。以下词语出现在初中物理教材中，但不在标准术语词典里。
请判断每个词语是否属于不规范的物理术语，如果是，请给出标准术语；如果不是，请说明“无需修改”。

词语：{unknown_words}

原文上下文（供参考）：{original_text}

请严格按照以下 Markdown 表格格式输出（必须包含表头分隔行 `|---|`）：

| 词语 | 是否不规范 | 标准术语（如需要） |
|------|------------|------------------|
| 示例 | 是 | 示例术语 |
| 示例2 | 否 | 无需修改 |

注意：
- 不要输出任何其他解释。
- 如果某个词语不需要修改，“标准术语”列填写“无需修改”。
""",
    input_variables=["original_text", "unknown_words"]
)

# ================== 8. 逻辑一致性检查提示词 ==================
LOGIC_PROMPT = PromptTemplate(
    template="""
你是一位初中物理教材审校专家。请判断以下来自同一教材不同章节的段落是否存在逻辑矛盾或前后不一致。

段落列表（已注明版本和章节）：
{passages}

要求：
1. 如果不存在明显矛盾，输出“✅ 逻辑一致”。
2. 如果存在矛盾，指出矛盾的具体内容，并说明哪一段落可能是错误的。
3. 尽量简短输出。
""",
    input_variables=["passages"]
)

# ================== 9. 辅助函数 ==================
def find_unknown_terms(text):
    """从文本中提取不在标准术语词典中的词（长度>1，非纯数字）"""
    words = set(jieba.lcut(text))
    words = {w for w in words if len(w) > 1 and not w.isdigit()}
    unknown = words - standard_terms
    return list(unknown)

def knowledge_review(text: str, context_docs: list) -> str:
    """基于检索段落进行知识审校，并生成版本对比表"""
    context_parts = []
    for doc in context_docs:
        source = f"【{doc['version']}】{doc['chapter_name']}"
        context_parts.append(f"{source}\n{doc['text']}")
    context = "\n\n".join(context_parts)
    prompt = KNOWLEDGE_PROMPT.format(question=text, context=context)
    return llm.predict(prompt)

def terminology_review(text: str) -> str:
    """术语检查：先匹配标准术语，再对未知词进行 LLM 判断"""
    words = set(jieba.lcut(text))
    matched_terms = [w for w in words if w in standard_terms and len(w) > 1]
    matched_terms = sorted(set(matched_terms))
    
    unknown_words = [w for w in words if w not in standard_terms and len(w) > 1 and not w.isdigit()]
    unknown_words = sorted(set(unknown_words))
    
    # 标准术语表格
    result = "### 标准术语（已识别）\n"
    if matched_terms:
        result += "| 术语 | 状态 |\n"
        result += "|------|------|\n"
        for term in matched_terms:
            result += f"| {term} | ✅ 规范 |\n"
    else:
        result += "未识别到标准术语。\n"
    
    # 疑似不规范术语表格
    result += "\n### 疑似不规范术语\n"
    if not unknown_words:
        result += "未发现疑似不规范的术语。\n"
    else:
        if len(unknown_words) > 15:
            unknown_words = unknown_words[:15]
        prompt = TERM_PROMPT.format(original_text=text[:1000], unknown_words=", ".join(unknown_words))
        llm_result = llm.predict(prompt)
        # 确保 LLM 返回的表格也包含分隔行（如果缺失则补充）
        if "|------|" not in llm_result and "| --- |" not in llm_result:
            # 尝试在第一个表头行后插入分隔行
            lines = llm_result.split("\n")
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                if i == 0 and line.strip().startswith("|") and "词语" in line:
                    # 插入分隔行
                    col_count = line.count("|") - 1
                    sep = "|" + "|".join(["------"] * col_count) + "|"
                    new_lines.append(sep)
            llm_result = "\n".join(new_lines)
        result += llm_result
    return result

def logic_consistency_review(query: str, context_docs: list) -> str:
    """逻辑一致性检查：基于检索到的同一知识点多个段落"""
    if len(context_docs) < 2:
        return "段落不足，无法进行逻辑一致性检查。"
    passages = []
    for i, doc in enumerate(context_docs, 1):
        passages.append(f"{i}. 【{doc['version']} {doc['chapter_name']}】\n{doc['text'][:500]}")
    prompt = LOGIC_PROMPT.format(passages="\n\n".join(passages))
    return llm.predict(prompt)

# ================== 10. 统一审校接口 ==================
def review_text(
    text: str,
    check_knowledge: bool = True,
    check_terminology: bool = True,
    check_logic: bool = True,
    top_k_per_version: int = 2,
    max_results: int = 15
) -> dict:
    """
    完整的审校函数
    返回格式：
    {
        "original_text": ...,
        "knowledge_review": "...",
        "terminology_review": "...",
        "logic_review": "...",
        "retrieved_docs": [...]   # 可选，用于调试
    }
    """
    # 1. 检索相关段落
    docs = retrieve_diverse_results(text, top_k_per_version=top_k_per_version, max_results=max_results)
    if not docs:
        return {
            "original_text": text,
            "error": "未找到相关参考语料，请检查数据库。"
        }
    
    result = {"original_text": text, "retrieved_docs": docs}
    
    # 2. 知识审校
    if check_knowledge:
        print("正在执行知识审校...")
        result["knowledge_review"] = knowledge_review(text, docs)
    
    # 3. 术语检查
    if check_terminology and standard_terms:
        print("正在执行术语检查...")
        result["terminology_review"] = terminology_review(text)
    
    # 4. 逻辑一致性检查
    if check_logic:
        print("正在执行逻辑一致性检查...")
        result["logic_review"] = logic_consistency_review(text, docs)
    
    return result

# ================== 11. 测试示例 ==================
if __name__ == "__main__":
    test_text = "水的沸点是100摄氏度。"
    print(f"待审文本：{test_text}\n")
    result = review_text(test_text)
    
    print("\n" + "="*40 + " 知识审校结果 " + "="*40)
    print(result.get("knowledge_review", "未执行"))
    
    print("\n" + "="*40 + " 术语检查结果 " + "="*40)
    print(result.get("terminology_review", "未执行（术语词典缺失）"))
    
    print("\n" + "="*40 + " 逻辑一致性检查 " + "="*40)
    print(result.get("logic_review", "未执行"))
    
    # 可选：查看检索到的文档（调试用）
    # print("\n检索到的文档数量：", len(result.get("retrieved_docs", [])))