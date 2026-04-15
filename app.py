import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
from review_module import review_text, call_deepseek

# ================== 页面配置 ==================
st.set_page_config(page_title="物理教材智能助手", layout="wide")

# ================== 初始化 session_state ==================
if "history" not in st.session_state:
    st.session_state.history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "current_input" not in st.session_state:
    st.session_state.current_input = ""
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "review"  
if "gen_history" not in st.session_state:
    st.session_state.gen_history = []
    # 默认审校模式

# ================== 侧边栏：功能选择 ==================
st.sidebar.title("导航")
mode = st.sidebar.radio(
    "选择功能",
    ["📖 审校助手", "✍️ 内容生成"],
    index=0 if st.session_state.app_mode == "review" else 1
)
st.session_state.app_mode = "review" if mode == "📖 审校助手" else "generate"

# ================== 审校模式 ==================
def render_review():
    # 侧边栏中的审校设置（仅在此模式下显示）
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ 审校设置")
        check_knowledge = st.checkbox("知识审校（含版本对比）", value=True)
        check_terminology = st.checkbox("术语检查", value=True)
        check_logic = st.checkbox("逻辑一致性检查", value=True)
        
        st.subheader("检索参数")
        top_k_per_version = st.number_input("每个版本取几个段落", min_value=1, max_value=5, value=2, step=1)
        max_results = st.number_input("最多返回段落数", min_value=5, max_value=30, value=15, step=5)
        
        st.markdown("---")
        st.header("📜 历史记录")
        if st.button("清空历史记录"):
            st.session_state.history = []
            st.session_state.current_result = None
            st.rerun()
        
        if st.session_state.history:
            for idx, item in enumerate(st.session_state.history):
                label = f"{item['timestamp']} - {item['input_preview'][:40]}..."
                if st.button(label, key=f"hist_{idx}"):
                    st.session_state.current_input = item["input_full"]
                    st.session_state.current_result = item["result"]
                    st.rerun()
        else:
            st.info("暂无历史记录")
    
    # 主区域
    st.title("📘 初中物理教材审校助手")
    
    # 输入方式
    tab1, tab2 = st.tabs(["✍️ 直接文本输入", "📁 上传文件"])
    input_text = ""
    with tab1:
        input_text = st.text_area("请输入待审校的教材文本", height=200, key="direct_input")
    with tab2:
        uploaded_file = st.file_uploader("上传 .txt 或 .md 文件", type=["txt", "md"])
        if uploaded_file is not None:
            try:
                input_text = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                input_text = uploaded_file.read().decode("gbk", errors="ignore")
            st.text_area("文件内容预览", input_text, height=200, disabled=True)
    
    col1, col2 = st.columns([1, 5])
    with col1:
        run_btn = st.button("🚀 开始审校", type="primary", use_container_width=True)
    with col2:
        export_btn = st.button("📥 导出当前结果为 JSON", use_container_width=True)
    
    # 处理审校
    if run_btn and input_text.strip():
        with st.spinner("正在审校，请稍候...（可能需要 10-20 秒）"):
            try:
                result = review_text(
                    text=input_text,
                    check_knowledge=check_knowledge,
                    check_terminology=check_terminology,
                    check_logic=check_logic,
                    top_k_per_version=top_k_per_version,
                    max_results=max_results
                )
                st.session_state.current_result = result
                st.session_state.current_input = input_text
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.history.insert(0, {
                    "timestamp": timestamp,
                    "input_preview": input_text[:50],
                    "input_full": input_text,
                    "result": result
                })
                if len(st.session_state.history) > 20:
                    st.session_state.history = st.session_state.history[:20]
                st.rerun()
            except Exception as e:
                st.error(f"审校失败：{str(e)}")
    elif run_btn and not input_text.strip():
        st.warning("请输入或上传待审校的文本内容。")
    
    # 展示结果
    if st.session_state.current_result:
        result = st.session_state.current_result
        st.markdown("---")
        st.header("🔍 审校结果")
        
        tab_know, tab_term, tab_logic, tab_ref = st.tabs(["📖 知识审校", "📝 术语检查", "🔗 逻辑一致性", "📚 参考段落"])
        with tab_know:
            if check_knowledge and "knowledge_review" in result:
                st.markdown(result["knowledge_review"])
            else:
                st.info("未开启知识审校或无结果。")
        with tab_term:
            if check_terminology and "terminology_review" in result:
                st.markdown(result["terminology_review"])
            else:
                st.info("未开启术语检查或无结果。")
        with tab_logic:
            if check_logic and "logic_review" in result:
                st.markdown(result["logic_review"])
            else:
                st.info("未开启逻辑一致性检查或无结果。")
        with tab_ref:
            if "retrieved_docs" in result and result["retrieved_docs"]:
                for i, doc in enumerate(result["retrieved_docs"]):
                    st.markdown(f"**{i+1}. 【{doc['version']}】{doc['chapter_name']}**")
                    st.text(doc["text"][:800] + ("..." if len(doc["text"]) > 800 else ""))
                    st.markdown("---")
            else:
                st.info("无参考段落。")
        if "error" in result:
            st.error(result["error"])
    
    # 导出 JSON
    if export_btn and st.session_state.current_result:
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "input_text": st.session_state.current_input,
            "settings": {
                "check_knowledge": check_knowledge,
                "check_terminology": check_terminology,
                "check_logic": check_logic,
                "top_k_per_version": top_k_per_version,
                "max_results": max_results
            },
            "result": st.session_state.current_result
        }
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 点击下载 JSON 文件",
            data=json_str,
            file_name=f"审校结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    elif export_btn:
        st.warning("没有可导出的结果，请先进行审校。")

# ================== 内容生成模式 ==================
def render_content_generation():
    st.title("✍️ 辅助内容生成")
    st.markdown("利用大模型辅助教材内容编写，支持习题批阅和习题生成。")
    
    # 创建三个标签页：习题批阅、习题生成、历史记录
    tab1, tab2, tab3 = st.tabs(["📝 习题批阅", "✨ 习题生成", "📜 历史记录"])
    
    # ========== 习题批阅 ==========
    with tab1:
        st.subheader("习题批阅")
        question = st.text_area("请输入题目", height=150, key="grading_question")
        student_answer = st.text_area("请输入学生答案", height=100, key="student_answer")
        if st.button("开始批阅", key="grade_btn"):
            if question and student_answer:
                with st.spinner("批阅中..."):
                    prompt = f"""请批阅以下初中物理习题，判断学生答案是否正确，并给出详细解析。
如果答案错误，请指出错误原因，并给出正确答案。
题目：{question}
学生答案：{student_answer}"""
                    result = call_deepseek(prompt)
                    st.markdown("### 批阅结果")
                    st.markdown(result)
                    # 保存历史
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.gen_history.insert(0, {
                        "type": "习题批阅",
                        "timestamp": timestamp,
                        "input_preview": question[:50] + "...",
                        "question": question,
                        "student_answer": student_answer,
                        "result": result
                    })
                    if len(st.session_state.gen_history) > 20:
                        st.session_state.gen_history = st.session_state.gen_history[:20]
            else:
                st.warning("请填写题目和学生答案")
    
    # ========== 习题生成 ==========
    with tab2:
        st.subheader("习题生成")
        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("知识点", key="topic_gen", placeholder="例如：欧姆定律")
            question_type = st.selectbox("题型", ["选择题", "填空题", "计算题", "简答题"], key="q_type")
        with col2:
            difficulty = st.selectbox("难度", ["容易", "中等", "较难"], key="difficulty")
            num_questions = st.slider("题数", min_value=1, max_value=5, value=1, key="num_q")
        
        if st.button("生成习题", key="gen_btn"):
            if topic:
                with st.spinner("生成中..."):
                    prompt = f"""请生成{num_questions}道初中物理关于「{topic}」的{difficulty}难度{question_type}。
要求：
- 每道题单独列出，标注题号
- 包含题目和参考答案
- 题目应贴合初中生认知水平
- 输出格式清晰，便于阅读"""
                    result = call_deepseek(prompt)
                    st.markdown("### 生成的习题")
                    st.markdown(result)
                    # 保存历史
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.gen_history.insert(0, {
                        "type": "习题生成",
                        "timestamp": timestamp,
                        "input_preview": f"{topic} ({question_type}, {difficulty}, {num_questions}题)",
                        "topic": topic,
                        "question_type": question_type,
                        "difficulty": difficulty,
                        "num_questions": num_questions,
                        "result": result
                    })
                    if len(st.session_state.gen_history) > 20:
                        st.session_state.gen_history = st.session_state.gen_history[:20]
            else:
                st.warning("请输入知识点")
    
    # ========== 历史记录 ==========
    with tab3:
        st.subheader("内容生成历史")
        if st.button("清空历史记录"):
            st.session_state.gen_history = []
            st.rerun()
        if not st.session_state.gen_history:
            st.info("暂无历史记录")
        else:
            for idx, item in enumerate(st.session_state.gen_history):
                with st.expander(f"{item['timestamp']} - {item['type']}: {item['input_preview']}"):
                    if item['type'] == "习题批阅":
                        st.markdown(f"**题目**: {item['question']}")
                        st.markdown(f"**学生答案**: {item['student_answer']}")
                        st.markdown(f"**批阅结果**:\n{item['result']}")
                    else:
                        st.markdown(f"**生成参数**: {item['input_preview']}")
                        st.markdown(f"**生成结果**:\n{item['result']}")

# ================== 主逻辑 ==================
if st.session_state.app_mode == "review":
    render_review()
else:
    render_content_generation()