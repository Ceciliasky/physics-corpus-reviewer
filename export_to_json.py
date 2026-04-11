import json
import re
from pathlib import Path

# ====== 配置 ======
CLEANED_DIR = Path("./cleaned_md")           # 章节文件目录
OUTPUT_JSON = Path("./enhanced_data.json")   # 输出 JSON 文件
PHYSICS_TERMS_FILE = Path("./physics_terms.txt")  # 物理术语词典（可选）

# ====== 加载物理术语（用于概念提取） ======
physics_terms = []
if PHYSICS_TERMS_FILE.exists():
    with open(PHYSICS_TERMS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            term = line.strip()
            if term:
                physics_terms.append(term)
else:
    print("警告：未找到 physics_terms.txt，将不进行概念提取。")

def parse_filename(filename: str):
    """从文件名解析元数据：版本_年级_册次_chXX_章名.md"""
    stem = Path(filename).stem
    pattern = re.compile(r'^(.+?)_(.+?)_(.+?)_ch(\d+)_(.+)$')
    match = pattern.match(stem)
    if not match:
        return None
    version, grade, volume, ch_num, chapter_name = match.groups()
    return {
        "version": version,
        "grade": grade,
        "volume": volume,
        "chapter_number": int(ch_num),
        "chapter_name": chapter_name
    }

def extract_concepts(text: str):
    """在文本中查找物理术语（简单子串匹配）"""
    if not physics_terms:
        return []
    found = set()
    for term in physics_terms:
        if term in text:
            found.add(term)
    return sorted(found)

def main():
    if not CLEANED_DIR.exists():
        print(f"错误：目录 {CLEANED_DIR} 不存在。")
        return

    md_files = list(CLEANED_DIR.glob("*.md"))
    if not md_files:
        print(f"错误：{CLEANED_DIR} 中没有 .md 文件。")
        return

    records = []
    for md_file in md_files:
        meta = parse_filename(md_file.name)
        if not meta:
            print(f"警告：文件名格式不匹配，跳过 {md_file.name}")
            continue
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        concepts = extract_concepts(content)
        records.append({
            "version": meta["version"],
            "grade": meta["grade"],
            "volume": meta["volume"],
            "chapter_number": meta["chapter_number"],
            "chapter_name": meta["chapter_name"],
            "content": content,
            "concepts": concepts   # 列表形式
        })

    # 按版本、年级、册次、章号排序
    records.sort(key=lambda x: (x["version"], x["grade"], x["volume"], x["chapter_number"]))

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"成功导出 JSON 文件：{OUTPUT_JSON}")
    print(f"共 {len(records)} 个章节。")

if __name__ == "__main__":
    main()