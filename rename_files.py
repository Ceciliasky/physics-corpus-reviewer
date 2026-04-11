import os
import re
from pathlib import Path

raw_dir = Path("./raw_md")
for file_path in raw_dir.glob("*.md"):
    old_name = file_path.name
    # 去除【】并提取版本、年级、册次
    # 例如 【北师大版】八年级上册_clean.md
    match = re.match(r'【(.+?)】(.+?)(上册|下册|全一册)_clean\.md', old_name)
    if not match:
        print(f"跳过不匹配的文件: {old_name}")
        continue
    version = match.group(1)      # 北师大版
    grade = match.group(2)        # 八年级
    volume = match.group(3)       # 上册/下册/全一册
    # 处理全一册：保持为“全一册”
    new_name = f"{version}_{grade}_{volume}.md"
    new_path = file_path.parent / new_name
    file_path.rename(new_path)
    print(f"重命名: {old_name} -> {new_name}")