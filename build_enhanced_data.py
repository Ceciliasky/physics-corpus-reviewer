import csv
import re
from pathlib import Path

CLEANED_DIR = Path("./cleaned_md")
OUTPUT_CSV = Path("./enhanced_data.csv")
PHYSICS_TERMS_FILE = Path("./physics_terms.txt")   # 核心概念词典（短词）

# 加载物理术语（每行一个词，支持短语）
physics_terms = []
if PHYSICS_TERMS_FILE.exists():
    with open(PHYSICS_TERMS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            term = line.strip()
            if term:
                physics_terms.append(term)
else:
    print("警告：物理术语词典不存在，将不进行概念标注。")

def parse_filename(filename: str):
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
    """在文本中查找出现的物理术语（不依赖分词）"""
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

    rows = []
    for md_file in md_files:
        meta = parse_filename(md_file.name)
        if not meta:
            print(f"警告：文件名格式不匹配，跳过 {md_file.name}")
            continue
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        concepts = extract_concepts(content)
        rows.append({
            "version": meta["version"],
            "grade": meta["grade"],
            "volume": meta["volume"],
            "chapter_number": meta["chapter_number"],
            "chapter_name": meta["chapter_name"],
            "content": content,
            "concepts": ",".join(concepts)
        })

    rows.sort(key=lambda x: (x["version"], x["grade"], x["volume"], x["chapter_number"]))

    with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ["version", "grade", "volume", "chapter_number", "chapter_name", "content", "concepts"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"成功生成增强数据：{OUTPUT_CSV}")
    print(f"共处理 {len(rows)} 个章节。")

if __name__ == "__main__":
    main()