import streamlit as st
import json
import time
from datetime import datetime
from review_module import review_text  # 确保 review_module.py 中的 review_text 函数可用

# ================== 页面配置 ==================
st.set_page_config(page_title="初中物理教材审校助手", layout="wide")
st.title("📘 初中物理教材审校助手")

# ================== 初始化 session_state ==================
if "history" not in st.session_state:
    st.session_state.history = []  # 每个元素: {"timestamp", "input_preview", "result", "input_full"}
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "current_input" not in st.session_state:
    st.session_state.current_input = ""

# ================== 侧边栏：审校设置 & 历史记录 ==================
with st.sidebar:
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
            # 显示时间戳和输入预览
            label = f"{item['timestamp']} - {item['input_preview'][:40]}..."
            if st.button(label, key=f"hist_{idx}"):
                st.session_state.current_input = item["input_full"]
                st.session_state.current_result = item["result"]
                st.rerun()
    else:
        st.info("暂无历史记录")

# ================== 主区域：输入方式选择 ==================
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

# ================== 审校按钮 ==================
col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 开始审校", type="primary", use_container_width=True)
with col2:
    export_btn = st.button("📥 导出当前结果为 JSON", use_container_width=True)

# ================== 处理审校 ==================
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
            # 保存当前结果
            st.session_state.current_result = result
            st.session_state.current_input = input_text
            # 添加到历史记录
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.history.insert(0, {
                "timestamp": timestamp,
                "input_preview": input_text[:50],
                "input_full": input_text,
                "result": result
            })
            # 只保留最近20条
            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[:20]
            st.rerun()
        except Exception as e:
            st.error(f"审校失败：{str(e)}")
elif run_btn and not input_text.strip():
    st.warning("请输入或上传待审校的文本内容。")

# ================== 展示结果 ==================
if st.session_state.current_result:
    result = st.session_state.current_result
    st.markdown("---")
    st.header("🔍 审校结果")
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📖 知识审校", "📝 术语检查", "🔗 逻辑一致性", "📚 参考段落"])
    
    with tab1:
        if check_knowledge and "knowledge_review" in result:
            st.markdown(result["knowledge_review"])
        else:
            st.info("未开启知识审校或无结果。")
    
    with tab2:
        if check_terminology and "terminology_review" in result:
            st.markdown(result["terminology_review"])
        else:
            st.info("未开启术语检查或无结果。")
    
    with tab3:
        if check_logic and "logic_review" in result:
            st.markdown(result["logic_review"])
        else:
            st.info("未开启逻辑一致性检查或无结果。")
    
    with tab4:
        if "retrieved_docs" in result and result["retrieved_docs"]:
            for i, doc in enumerate(result["retrieved_docs"]):
                st.markdown(f"**{i+1}. 【{doc['version']}】{doc['chapter_name']}**")
                st.text(doc["text"][:800] + ("..." if len(doc["text"]) > 800 else ""))
                st.markdown("---")
        else:
            st.info("无参考段落。")
    
    # 错误信息（如果有）
    if "error" in result:
        st.error(result["error"])

# ================== 导出 JSON ==================
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