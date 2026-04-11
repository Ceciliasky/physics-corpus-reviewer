import re
from pathlib import Path

CLEANED_DIR = Path("./cleaned_md")   # 存放手动拆分好的章节文件

# ----- 1. 升级子标题（包括常见的物理板块名称）-----
# 关键词匹配：这些词单独成行时，升级为 ####
SUBHEADING_KEYWORDS = [
    "认识", "探究", "描述", "什么是", "了解", "活动", "实验", "猜想", "原理", "结构", "作用",
    "科学窗", "交流讨论", "实践活动", "实验探究", "自我检测", "拓展阅读", "信息浏览", "STS", "金钥匙"
]

def upgrade_subheadings(text):
    lines = text.splitlines()
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 条件：非空、不是已有标题、不以标点结尾、长度<=40、只含中英文数字空格、匹配关键词或前后空行
        if (stripped and 
            not stripped.startswith('#') and
            not stripped.endswith(('。', '？', '！', '：', '.', '?', '!', ':')) and
            len(stripped) <= 40 and
            re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9\s]+$', stripped) and
            (any(kw in stripped for kw in SUBHEADING_KEYWORDS) or 
             (i > 0 and lines[i-1].strip() == '') and (i < len(lines)-1 and lines[i+1].strip() != ''))):
            new_lines.append(f"#### {stripped}")
        else:
            new_lines.append(line)
    return "\n".join(new_lines)

# ----- 2. 修复表格 -----
def fix_markdown_table(text):
    lines = text.splitlines()
    in_table = False
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # 判断是否为表格行（包含 '|' 且不是标题行、代码块）
        if '|' in stripped and not stripped.startswith('#') and not stripped.startswith('```'):
            if not in_table:
                # 新表格开始，检查下一行是否为分隔行
                in_table = True
                # 确保当前行以 '|' 开头和结尾
                if not stripped.startswith('|'):
                    stripped = '|' + stripped
                if not stripped.endswith('|'):
                    stripped = stripped + '|'
                # 检查下一行是否存在且为分隔行
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if not (next_line and '|' in next_line and re.match(r'^[\|\s\-:]+$', next_line)):
                        # 下一行不是分隔行，需要插入一行分隔行
                        # 根据当前表头的列数生成分隔行（按 '|' 分割，减2是因为首尾空）
                        num_cols = stripped.count('|') - 1
                        sep_row = '|' + '|'.join(['---'] * num_cols) + '|'
                        fixed_lines.append(stripped)
                        fixed_lines.append(sep_row)
                        i += 1
                        continue
                fixed_lines.append(stripped)
            else:
                # 已经在表格中，处理数据行或分隔行
                if not stripped.startswith('|'):
                    stripped = '|' + stripped
                if not stripped.endswith('|'):
                    stripped = stripped + '|'
                # 如果是分隔行（只包含 |、-、:、空格），规范化为 |---|
                if re.match(r'^[\|\s\-:]+$', stripped):
                    parts = stripped.split('|')
                    new_parts = ['|']
                    for p in parts[1:-1]:
                        if p.strip() == '':
                            new_parts.append('---|')
                        else:
                            new_parts.append(p + '|')
                    stripped = ''.join(new_parts)
                fixed_lines.append(stripped)
        else:
            if in_table:
                in_table = False
            fixed_lines.append(line)
        i += 1
    return "\n".join(fixed_lines)

# ----- 3. 用标签包裹特定板块 -----
BLOCKS = [
    (re.compile(r'^活动\d+[\.\s]', re.MULTILINE), 'activity'),
    (re.compile(r'^自我评价与作业', re.MULTILINE), 'self-assessment'),
    (re.compile(r'^课外活动', re.MULTILINE), 'extra-activity'),
    (re.compile(r'^信息浏览', re.MULTILINE), 'info'),
    (re.compile(r'^STS', re.MULTILINE), 'sts'),
    (re.compile(r'^金钥匙', re.MULTILINE), 'golden-key'),
]

def wrap_blocks(text):
    lines = text.splitlines()
    result_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        matched = False
        for pattern, tag in BLOCKS:
            if pattern.match(line):
                block_lines = [line]
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if any(p.match(nxt) for p, _ in BLOCKS):
                        break
                    if nxt.strip() == '' and j+1 < len(lines) and lines[j+1].strip() == '':
                        break
                    block_lines.append(nxt)
                    j += 1
                block_id = f"{tag}_{i}"
                block_text = "\n".join(block_lines)
                wrapped = f"<{tag} id=\"{block_id}\">\n{block_text}\n</{tag}>"
                result_lines.append(wrapped)
                i = j
                matched = True
                break
        if not matched:
            result_lines.append(line)
            i += 1
    return "\n".join(result_lines)

# ----- 主流程 -----
def process_file(file_path):
    print(f"处理: {file_path.name}")
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = upgrade_subheadings(text)
    text = fix_markdown_table(text)
    text = wrap_blocks(text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"  完成")

def main():
    md_files = list(CLEANED_DIR.glob("*.md"))
    if not md_files:
        print(f"错误：{CLEANED_DIR} 中没有 .md 文件。")
        return
    for md_file in md_files:
        process_file(md_file)
    print("所有章节文件预处理完成！")

if __name__ == "__main__":
    main()