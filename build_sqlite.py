import sqlite3
import re
import json
from pathlib import Path

CLEANED_DIR = Path("./cleaned_md")
DB_PATH = Path("./physics_corpus.db")
PHYSICS_TERMS_FILE = Path("./physics_terms.txt")

# 加载术语
physics_terms = []
if PHYSICS_TERMS_FILE.exists():
    with open(PHYSICS_TERMS_FILE, 'r', encoding='utf-8') as f:
        physics_terms = [line.strip() for line in f if line.strip()]

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
    found = set()
    for term in physics_terms:
        if term in text:
            found.add(term)
    return list(found)

def main():
    if not CLEANED_DIR.exists():
        print(f"错误：{CLEANED_DIR} 不存在")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            grade TEXT,
            volume TEXT,
            chapter_number INTEGER,
            chapter_name TEXT,
            content TEXT,
            concepts TEXT
        )
    ''')
    conn.commit()

    for md_file in CLEANED_DIR.glob("*.md"):
        meta = parse_filename(md_file.name)
        if not meta:
            print(f"跳过：{md_file.name}")
            continue
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        concepts = extract_concepts(content)
        cursor.execute('''
            INSERT INTO chapters (version, grade, volume, chapter_number, chapter_name, content, concepts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (meta["version"], meta["grade"], meta["volume"], meta["chapter_number"],
              meta["chapter_name"], content, ",".join(concepts)))
    conn.commit()
    conn.close()
    print(f"SQLite 数据库已创建：{DB_PATH}")

if __name__ == "__main__":
    main()