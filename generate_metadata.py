import json
import re
from pathlib import Path

CLEANED_DIR = Path("./cleaned_md")
OUTPUT_JSON = Path("./metadata.json")

def parse_filename(filename: str):
    stem = Path(filename).stem
    # 正则：版本_年级_册次_ch(\d+)_(.+)
    pattern = re.compile(r'^(.+?)_(.+?)_(.+?)_ch(\d+)_(.+)$')
    match = pattern.match(stem)
    if not match:
        print(f"警告：文件名格式不匹配，跳过：{filename}")
        return None
    version, grade, volume, ch_num, chapter_name = match.groups()
    return {
        "file_name": filename,
        "version": version,
        "grade": grade,
        "volume": volume,
        "chapter_number": int(ch_num),
        "chapter_name": chapter_name,
        "file_path": str(CLEANED_DIR / filename)
    }

def main():
    if not CLEANED_DIR.exists():
        print(f"错误：目录 {CLEANED_DIR} 不存在")
        return
    md_files = list(CLEANED_DIR.glob("*.md"))
    if not md_files:
        print(f"错误：{CLEANED_DIR} 中没有 .md 文件")
        return
    metadata = []
    for md_file in md_files:
        meta = parse_filename(md_file.name)
        if meta:
            metadata.append(meta)
    metadata.sort(key=lambda x: (x["version"], x["grade"], x["volume"], x["chapter_number"]))
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"成功生成 {OUTPUT_JSON}，共 {len(metadata)} 个章节")

if __name__ == "__main__":
    main()