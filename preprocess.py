"""
教材语料库预处理脚本
功能：
1. 删除尾部无关内容
2. 升级子标题
3. 修复表格格式
4. 标注教学块
5. 按章切分
6. 生成元数据 JSON
"""

import re
import json
import string
from pathlib import Path

# ================== 配置 ==================
RAW_DIR = Path("./raw_md")
CLEANED_DIR = Path("./cleaned_md")
LOG_DIR = Path("./logs")
CLEANED_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ================== 1. 删除尾部无关内容 ==================
TAIL_KEYWORDS = ["后记", "说明", "你怎样学习", "欢迎将这张表填好后寄给我们", "物理", "九年级 下册"]
def remove_tail(text):
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if any(line.strip().startswith(kw) for kw in TAIL_KEYWORDS):
            break
        new_lines.append(line)
    return "\n".join(new_lines)

# ================== 2. 升级子标题 ==================
SUBHEADING_KEYWORDS = ["认识", "探究", "描述", "什么是", "了解", "活动", "实验", "猜想", "原理", "结构", "作用"]
def upgrade_subheadings(text):
    lines = text.splitlines()
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (stripped and 
            not stripped.startswith('#') and
            not stripped.endswith(('。', '？', '！', '：', '.', '?', '!', ':')) and
            len(stripped) <= 30 and
            re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9\s]+$', stripped) and
            (any(kw in stripped for kw in SUBHEADING_KEYWORDS) or 
             (i > 0 and lines[i-1].strip() == '') and (i < len(lines)-1 and lines[i+1].strip() != ''))):
            new_lines.append(f"#### {stripped}")
        else:
            new_lines.append(line)
    return "\n".join(new_lines)

# ================== 3. 修复表格 ==================
def fix_markdown_table(text):
    lines = text.splitlines()
    in_table = False
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if '|' in stripped and not stripped.startswith('#') and not stripped.startswith('```'):
            if not in_table:
                in_table = True
            if not stripped.startswith('|'):
                stripped = '|' + stripped
            if not stripped.endswith('|'):
                stripped = stripped + '|'
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
    return "\n".join(fixed_lines)

# ================== 4. 标注教学块 ==================
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

# ================== 5. 辅助函数 ==================
def chinese_to_arabic(chinese_num: str) -> int:
    """支持中文数字 一 ~ 九十九（含十一、二十、二十一）"""
    chinese_digits = {
        '零':0, '一':1, '二':2, '三':3, '四':4,
        '五':5, '六':6, '七':7, '八':8, '九':9
    }
    if not chinese_num:
        return 0
    # 直接映射 0-9
    if chinese_num in chinese_digits:
        return chinese_digits[chinese_num]
    # 处理 十
    if chinese_num == '十':
        return 10
    # 处理 十一 ~ 十九
    if chinese_num.startswith('十') and len(chinese_num) == 2:
        return 10 + chinese_digits.get(chinese_num[1], 0)
    # 处理 二十 ~ 九十九
    if len(chinese_num) == 2 and chinese_num[1] == '十':
        # 二十、三十...
        return chinese_digits.get(chinese_num[0], 0) * 10
    if len(chinese_num) == 3 and chinese_num[1] == '十':
        # 二十一、二十二...
        tens = chinese_digits.get(chinese_num[0], 0) * 10
        ones = chinese_digits.get(chinese_num[2], 0)
        return tens + ones
    return 0

def sanitize_filename(name: str) -> str:
    """清理字符串，确保可作为合法文件名"""
    # 替换换行、回车、制表为空格
    name = name.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # 删除全角空格和不断行空格
    name = name.replace('\u3000', ' ').replace('\u00A0', ' ')
    # 删除控制字符
    name = ''.join(ch for ch in name if ord(ch) >= 32 or ch == ' ')
    # 删除非法字符 \ / : * ? " < > |
    illegal_chars = r'[\\/*?:"<>|]'
    name = re.sub(illegal_chars, '', name)
    # 合并连续空格
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    if not name:
        name = "untitled"
    # 限制长度
    return name[:50]

# ================== 6. 按章切分 ==================
def split_by_chapter(text, file_stem):
    """
    鲁棒的章切分函数，支持多种标题格式：
    - ## 第一章 内容
    - ## 第1章 内容
    - ## 第 一 章 内容（带空格）
    - # 第一章 内容（一级标题）
    - ## 1 内容（无“第”字）
    """
    # 解析版本、年级、册次
    parts = file_stem.split('_')
    if len(parts) >= 3:
        version = parts[0]
        grade = parts[1]
        volume = parts[2]
    else:
        version = "unknown"
        grade = "unknown"
        volume = "unknown"
    
    lines = text.splitlines()
    chapter_indices = []
    chapter_titles = []
    
    # 多种匹配模式（按优先级）
    patterns = [
        # 标准格式：## 第一章 或 ## 第1章
        re.compile(r'^(#{1,2})\s+第\s*([一二三四五六七八九十\d]+)\s*章\s+(.+)$'),
        # 无“第”字：## 1 内容 或 ## 一 内容
        re.compile(r'^(#{1,2})\s+([一二三四五六七八九十\d]+)\s+(.+)$'),
        # 宽松匹配：行中包含“第X章”且以#开头
        re.compile(r'^(#{1,2})\s+(?:第\s*([一二三四五六七八九十\d]+)\s*章)\s*(.*)$'),
    ]
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped.startswith('#'):
            continue
        matched = False
        for pattern in patterns:
            m = pattern.match(line_stripped)
            if m:
                # 提取章号（可能是中文或数字）
                if len(m.groups()) == 3:
                    # 格式1和3：章号在第二个捕获组
                    num_str = m.group(2)
                    title = m.group(3)
                else:  # 格式2：章号在第二个捕获组，标题在第三个
                    num_str = m.group(2)
                    title = m.group(3) if len(m.groups()) > 2 else ''
                # 转换中文数字
                if num_str.isdigit():
                    ch_num = num_str
                else:
                    arabic = chinese_to_arabic(num_str)
                    if arabic == 0:
                        ch_num = str(len(chapter_indices)+1)  # 后备
                    else:
                        ch_num = str(arabic)
                chapter_indices.append(i)
                # 保存标题（去掉开头的#和多余空格）
                full_title = line_stripped
                chapter_titles.append((full_title, ch_num, title))
                matched = True
                break
        # 可选：如果一行有“第X章”但没被正则匹配，可以额外处理
        if not matched and '第' in line_stripped and '章' in line_stripped and line_stripped.startswith('#'):
            print(f"  未匹配但疑似章标题: {line_stripped[:50]}")
    
    # 如果没有找到任何章标题，将整个文件作为一章
    if not chapter_indices:
        print(f"  警告：未找到章标题，将整个文件作为一章处理")
        chap_title = file_stem
        chap_id = f"{version}_{grade}_{volume}_ch01_{sanitize_filename(chap_title)}"
        return [(chap_id, chap_title, text)]
    
    # 按索引切分内容
    chapters = []
    for idx, start_line in enumerate(chapter_indices):
        end_line = chapter_indices[idx+1] if idx+1 < len(chapter_indices) else len(lines)
        chapter_lines = lines[start_line:end_line]
        full_title, ch_num, title = chapter_titles[idx]
        
        # 清理标题（如果title为空则从full_title提取）
        if not title.strip():
            # 移除开头的#和数字部分
            clean = re.sub(r'^(#{1,2})\s+(?:第\s*\d+\s*章\s*)?', '', full_title)
            title = clean.strip()
        
        chap_title = title if title else f"第{ch_num}章"
        # 进一步清理
        chap_title = re.sub(r'[\u3000\u00A0]', ' ', chap_title)
        chap_title = re.sub(r'\s+', ' ', chap_title).strip()
        
        # 构造文档ID
        chap_id = f"{version}_{grade}_{volume}_ch{int(ch_num):02d}_{sanitize_filename(chap_title)}"
        chap_content = "\n".join(chapter_lines).strip()
        chapters.append((chap_id, chap_title, chap_content))
    
    print(f"  找到 {len(chapters)} 个章标题: {[c[1][:30] for c in chapters]}")
    return chapters

# ================== 7. 主流程 ==================
def process_file(md_path):
    print(f"处理文件: {md_path.name}")
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(md_path, 'r', encoding='gbk') as f:
            text = f.read()
    
    text = remove_tail(text)
    text = upgrade_subheadings(text)
    text = fix_markdown_table(text)
    text = wrap_blocks(text)
    
    file_stem = md_path.stem
    chapters = split_by_chapter(text, file_stem)
    
    metadata = []
    for chap_id, chap_title, chap_content in chapters:
        out_path = CLEANED_DIR / f"{chap_id}.md"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(chap_content)
        metadata.append({
            "doc_id": chap_id,
            "source_file": md_path.name,
            "chapter_title": chap_title,
            "file_path": str(out_path)
        })
    meta_path = CLEANED_DIR / f"{file_stem}_metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"  完成，生成 {len(chapters)} 个章节文件")
    with open(LOG_DIR / "process.log", "a", encoding="utf-8") as f:
        f.write(f"{md_path.name} -> {len(chapters)} chapters\n")

def main():
    md_files = list(RAW_DIR.glob("*.md")) + list(RAW_DIR.glob("*.txt"))
    if not md_files:
        print("错误：raw_md 文件夹中没有 .md 或 .txt 文件。")
        return
    for md_path in md_files:
        process_file(md_path)
    print("全部处理完成！结果保存在 cleaned_md/ 目录下。")

if __name__ == "__main__":
    main()