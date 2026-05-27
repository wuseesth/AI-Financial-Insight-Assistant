"""
AI 金融信息分析助手 (AI Financial Insight Assistant)
==================================================
主入口文件 - Streamlit 多页面应用

功能模块：
1. 📰 财经新闻分析 - 自动总结、利好利空分析
2. 📋 上市公司公告分析 - 核心事件提取、财务数据分析
3. 🔥 市场热点分析 - 热点话题、热门行业/公司提取
4. 🔍 股票深度解码 - CFA视角多维度深度解码（市场归属、异动规则、资金行为、策略建议）

技术栈：Python + Streamlit + DeepSeek/OpenAI API
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any

# 项目内部模块
from services.api_client import APIClient, get_available_backends, get_backend_models
from prompts.financial_prompts import PromptManager
from utils.helpers import parse_json_response
from utils.config import AppConfig

# ============================================================
# 页面配置（必须在第一个 st 命令之前）
# ============================================================
st.set_page_config(**AppConfig.PAGE_CONFIG)

# ============================================================
# 自定义 CSS - 金融科技深色主题
# ============================================================
def load_css():
    """加载自定义 CSS 样式"""
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0E1117 0%, #1A1D27 50%, #0E1117 100%);
        }
        .app-header {
            text-align: center;
            padding: 1.5rem 0;
            margin-bottom: 2rem;
            background: linear-gradient(135deg, #00D4AA 0%, #00A3FF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: 2px;
        }
        .app-subtitle {
            text-align: center;
            color: #8892B0;
            font-size: 1rem;
            margin-top: -1.5rem;
            margin-bottom: 2rem;
        }
        .card {
            background: linear-gradient(145deg, #1A1D27, #222639);
            border: 1px solid #2A2D3E;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(0, 212, 170, 0.1);
        }
        .result-card {
            background: linear-gradient(145deg, #1A1D27, #222639);
            border: 1px solid #2A2D3E;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .result-section {
            margin: 1rem 0;
            padding: 1rem;
            background: rgba(0, 212, 170, 0.05);
            border-left: 3px solid #00D4AA;
            border-radius: 0 8px 8px 0;
        }
        .result-label {
            color: #00D4AA;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .result-value {
            color: #E8E8E8;
            line-height: 1.6;
        }
        .tag {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            margin: 0.25rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .tag-bullish {
            background: rgba(0, 212, 170, 0.15);
            color: #00D4AA;
            border: 1px solid rgba(0, 212, 170, 0.3);
        }
        .tag-bearish {
            background: rgba(255, 77, 77, 0.15);
            color: #FF4D4D;
            border: 1px solid rgba(255, 77, 77, 0.3);
        }
        .tag-neutral {
            background: rgba(255, 193, 7, 0.15);
            color: #FFC107;
            border: 1px solid rgba(255, 193, 7, 0.3);
        }
        .tag-industry {
            background: rgba(0, 163, 255, 0.15);
            color: #00A3FF;
            border: 1px solid rgba(0, 163, 255, 0.3);
        }
        .tag-company {
            background: rgba(156, 39, 176, 0.15);
            color: #CE93D8;
            border: 1px solid rgba(156, 39, 176, 0.3);
        }
        .tag-risk {
            background: rgba(255, 152, 0, 0.15);
            color: #FF9800;
            border: 1px solid rgba(255, 152, 0, 0.3);
        }
        .metric-card {
            text-align: center;
            padding: 1rem;
            background: rgba(0, 212, 170, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(0, 212, 170, 0.1);
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #00D4AA;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #8892B0;
            margin-top: 0.25rem;
        }
        .stButton > button {
            background: linear-gradient(135deg, #00D4AA, #00A3FF) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 2rem !important;
            font-weight: 600 !important;
            transition: all 0.3s !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(0, 212, 170, 0.4) !important;
        }
        .stTextArea textarea {
            background: #1A1D27 !important;
            border: 1px solid #2A2D3E !important;
            border-radius: 12px !important;
            color: #E8E8E8 !important;
            font-size: 0.95rem !important;
        }
        .stTextArea textarea:focus {
            border-color: #00D4AA !important;
            box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.2) !important;
        }
        .stSelectbox > div > div {
            background: #1A1D27 !important;
            border: 1px solid #2A2D3E !important;
            border-radius: 8px !important;
            color: #E8E8E8 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: #1A1D27;
            padding: 0.5rem;
            border-radius: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            color: #8892B0 !important;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #00D4AA, #00A3FF) !important;
            color: white !important;
        }
        .stProgress > div > div {
            background: linear-gradient(135deg, #00D4AA, #00A3FF) !important;
        }
        hr {
            border-color: #2A2D3E !important;
            margin: 2rem 0 !important;
        }
        .footer {
            text-align: center;
            color: #4A4D5E;
            font-size: 0.8rem;
            padding: 2rem 0;
            border-top: 1px solid #2A2D3E;
            margin-top: 3rem;
        }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #1A1D27; }
        ::-webkit-scrollbar-thumb { background: #2A2D3E; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3A3D4E; }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 会话状态初始化
# ============================================================
def init_session_state():
    """初始化 Streamlit 会话状态"""
    defaults = {
        "api_configured": False,
        "api_client": None,
        "backend": AppConfig.DEFAULT_BACKEND,
        "model": AppConfig.DEFAULT_MODEL,
        "api_key": "",
        "analysis_history": [],
        "current_page": "news_analysis",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# 侧边栏
# ============================================================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 3rem;">📈</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #00D4AA; margin-top: 0.5rem;">
                AI Financial Insight
            </div>
            <div style="font-size: 0.8rem; color: #8892B0;">v1.0.0</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # API 配置区域
        st.markdown('<div style="color: #00D4AA; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;">🔑 API 配置</div>', unsafe_allow_html=True)

        backends = get_available_backends()
        selected_backend = st.selectbox(
            "选择 API 后端",
            backends,
            index=backends.index(st.session_state.backend)
                if st.session_state.backend in backends else 0,
            key="sidebar_backend",
            label_visibility="collapsed",
        )

        models = get_backend_models(selected_backend)
        selected_model = st.selectbox(
            "选择模型",
            models,
            index=models.index(st.session_state.model)
                if st.session_state.model in models else 0,
            key="sidebar_model",
            label_visibility="collapsed",
        )

        env_key = AppConfig.get_env_api_key(selected_backend)
        key_placeholder = "已从环境变量读取" if env_key else "请输入 API Key"
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder=key_placeholder,
            value=st.session_state.api_key,
            key="sidebar_api_key",
            label_visibility="collapsed",
            help=f"如已设置 {selected_backend.upper()}_API_KEY 环境变量则无需填写",
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            connect_btn = st.button("🔌 连接", use_container_width=True)
        with col2:
            status_icon = "🟢" if st.session_state.api_configured else "🔴"
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px; font-size: 1.2rem;'>{status_icon}</div>",
                unsafe_allow_html=True,
            )

        if connect_btn:
            connect_api(selected_backend, selected_model, api_key or env_key)

        if st.session_state.api_configured:
            st.markdown(f"""
            <div style="background: rgba(0, 212, 170, 0.1); border: 1px solid rgba(0, 212, 170, 0.2);
                        border-radius: 8px; padding: 0.5rem 1rem; margin: 1rem 0;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%;
                     background:#00D4AA; box-shadow:0 0 8px rgba(0,212,170,0.5); margin-right:6px;"></span>
                <span style="color: #00D4AA; font-size: 0.85rem;">API 已连接</span><br>
                <span style="color: #8892B0; font-size: 0.75rem;">
                    {st.session_state.backend.upper()} / {st.session_state.model}
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # 功能模块导航
        st.markdown('<div style="color: #00D4AA; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;">📊 功能模块</div>', unsafe_allow_html=True)

        modules = AppConfig.get_enabled_modules()
        for module_key, module_config in modules.items():
            btn_label = f"{module_config['icon']} {module_config['name']}"
            if st.button(
                btn_label,
                use_container_width=True,
                key=f"nav_{module_key}",
                type="secondary" if st.session_state.current_page != module_key else "primary",
            ):
                st.session_state.current_page = module_key
                st.rerun()

        st.markdown("---")

        # 使用统计
        st.markdown('<div style="color: #00D4AA; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;">📈 使用统计</div>', unsafe_allow_html=True)
        history_count = len(st.session_state.analysis_history)
        st.markdown(
            f'<div style="color: #8892B0; font-size: 0.85rem; text-align: center;">'
            f'本次会话分析次数: <span style="color: #00D4AA; font-weight: 700;">{history_count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if history_count > 0 and st.button("🗑️ 清空历史", use_container_width=True):
            st.session_state.analysis_history = []
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #4A4D5E; font-size: 0.7rem; padding: 1rem 0;">
            <div>Powered by AI</div>
            <div style="margin-top: 0.25rem;">© 2024 Financial Insight</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# API 连接逻辑
# ============================================================
def connect_api(backend: str, model: str, api_key: str):
    """连接 API 服务"""
    if not api_key:
        st.error("❌ 请提供 API Key 或设置环境变量")
        return

    try:
        with st.spinner(f"🔄 正在连接 {backend.upper()}..."):
            client = APIClient(
                api_key=api_key,
                backend=backend,
                model=model,
            )
            test_msg = [{"role": "user", "content": "Hello"}]
            client.chat(test_msg, max_tokens=10)

            st.session_state.api_client = client
            st.session_state.api_configured = True
            st.session_state.backend = backend
            st.session_state.model = model
            st.session_state.api_key = api_key

            st.success(f"✅ 成功连接到 {backend.upper()} ({model})")
            time.sleep(0.5)
            st.rerun()

    except Exception as e:
        st.error(f"❌ 连接失败: {str(e)}")
        st.session_state.api_configured = False
        st.session_state.api_client = None


# ============================================================
# 分析结果渲染
# ============================================================
def render_analysis_result(result: Dict[str, Any], analysis_type: str):
    """渲染分析结果"""
    if "error" in result:
        st.error(f"❌ 分析出错: {result['error']}")
        if "raw_content" in result:
            with st.expander("查看原始返回内容"):
                st.text(result["raw_content"])
        return

    if analysis_type == "news_analysis":
        render_news_result(result)
    elif analysis_type == "announcement_analysis":
        render_announcement_result(result)
    elif analysis_type == "hotspot_analysis":
        render_hotspot_result(result)
    elif analysis_type == "stock_deep_decode":
        try:
            render_stock_decode_result(result)
        except Exception as e:
            st.error(f"❌ 渲染分析结果时出错: {str(e)}")
            with st.expander("查看原始返回数据"):
                st.json(result)


def render_news_result(result: Dict[str, Any]):
    """渲染财经新闻分析结果"""
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    st.markdown("### 📝 新闻总结")
    st.markdown(
        f'<div class="result-section"><div class="result-value">{result.get("summary", "无")}</div></div>',
        unsafe_allow_html=True,
    )

    sentiment = result.get("sentiment", {})
    judgment = sentiment.get("judgment", "中性")
    confidence = sentiment.get("confidence", 0)
    reason = sentiment.get("reason", "")

    tag_class = {
        "利好": "tag-bullish",
        "利空": "tag-bearish",
        "中性": "tag-neutral",
    }.get(judgment, "tag-neutral")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div class="metric-card">'
            f'<div><span class="tag {tag_class}" style="font-size: 1rem;">{judgment}</span></div>'
            f'<div class="metric-label">情绪判断</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{confidence}%</div>'
            f'<div class="metric-label">置信度</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="result-value" style="font-size: 0.9rem;">{result.get("recommendation", "观望")}</div>'
            f'<div class="metric-label">投资建议</div></div>',
            unsafe_allow_html=True,
        )

    if reason:
        st.markdown(
            f'<div class="result-section"><div class="result-label">判断依据</div>'
            f'<div class="result-value">{reason}</div></div>',
            unsafe_allow_html=True,
        )

    industries = result.get("industries", [])
    if industries:
        st.markdown("### 🏭 涉及行业")
        tags = "".join(f'<span class="tag tag-industry">{ind}</span>' for ind in industries)
        st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

    companies = result.get("companies", [])
    if companies:
        st.markdown("### 🏢 涉及公司")
        tags = "".join(f'<span class="tag tag-company">{comp}</span>' for comp in companies)
        st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

    risks = result.get("risks", [])
    if risks:
        st.markdown("### ⚠️ 风险提示")
        for risk in risks:
            st.markdown(
                f'<span class="tag tag-risk">⚠</span> '
                f'<span style="color: #E8E8E8;">{risk}</span><br>',
                unsafe_allow_html=True,
            )

    market_impact = result.get("market_impact", {})
    if market_impact:
        st.markdown("### 📊 市场影响")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="result-section">'
                f'<div class="result-label">短期影响</div>'
                f'<div class="result-value">{market_impact.get("short_term", "无")}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="result-section">'
                f'<div class="result-label">长期影响</div>'
                f'<div class="result-value">{market_impact.get("long_term", "无")}</div></div>',
                unsafe_allow_html=True,
            )

    key_points = result.get("key_points", [])
    if key_points:
        st.markdown("### 🔑 关键要点")
        for i, point in enumerate(key_points, 1):
            st.markdown(
                f'<div style="color: #E8E8E8; margin: 0.3rem 0;">'
                f'<span style="color: #00D4AA;">{i}.</span> {point}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


def render_announcement_result(result: Dict[str, Any]):
    """渲染公告分析结果"""
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    st.markdown("### 🎯 核心事件")
    st.markdown(
        f'<div class="result-section"><div class="result-value">{result.get("core_event", "无")}</div></div>',
        unsafe_allow_html=True,
    )

    event_type = result.get("event_type", "其他")
    st.markdown(
        f'<div style="margin: 1rem 0;"><span class="tag tag-industry">📌 {event_type}</span></div>',
        unsafe_allow_html=True,
    )

    financial_data = result.get("financial_data", {})
    if financial_data:
        st.markdown("### 💰 财务数据")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">营业收入</div>'
                f'<div class="result-value" style="font-size: 1rem;">{financial_data.get("revenue", "未提及")}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">增长率</div>'
                f'<div class="result-value" style="font-size: 1rem;">{financial_data.get("growth_rate", "未提及")}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">净利润</div>'
                f'<div class="result-value" style="font-size: 1rem;">{financial_data.get("net_profit", "未提及")}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">其他指标</div>'
                f'<div class="result-value" style="font-size: 1rem;">{financial_data.get("other_metrics", "未提及")}</div></div>',
                unsafe_allow_html=True,
            )

    impact = result.get("impact_analysis", {})
    if impact:
        st.markdown("### 📊 影响分析")
        col1, col2 = st.columns(2)
        with col1:
            positive = impact.get("positive", [])
            if positive:
                st.markdown(
                    f'<div class="result-section" style="border-left-color: #00D4AA;">'
                    f'<div class="result-label" style="color: #00D4AA;">✅ 正面影响</div>'
                )
                for p in positive:
                    st.markdown(f'<div class="result-value">• {p}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            negative = impact.get("negative", [])
            if negative:
                st.markdown(
                    f'<div class="result-section" style="border-left-color: #FF4D4D;">'
                    f'<div class="result-label" style="color: #FF4D4D;">❌ 负面影响</div>'
                )
                for n in negative:
                    st.markdown(f'<div class="result-value">• {n}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    risks = result.get("risks", [])
    if risks:
        st.markdown("### ⚠️ 风险提示")
        for risk in risks:
            st.markdown(
                f'<span class="tag tag-risk">⚠</span> '
                f'<span style="color: #E8E8E8;">{risk}</span><br>',
                unsafe_allow_html=True,
            )

    market_impact = result.get("market_impact", "")
    if market_impact:
        st.markdown("### 📈 市场影响")
        st.markdown(
            f'<div class="result-section"><div class="result-value">{market_impact}</div></div>',
            unsafe_allow_html=True,
        )

    advice = result.get("investor_advice", "")
    if advice:
        st.markdown("### 💡 投资者建议")
        st.markdown(
            f'<div class="result-section" style="border-left-color: #FFC107;">'
            f'<div class="result-value">{advice}</div></div>',
            unsafe_allow_html=True,
        )

    deadlines = result.get("key_deadlines", [])
    if deadlines:
        st.markdown("### 📅 关键时间节点")
        for d in deadlines:
            st.markdown(
                f'<div style="color: #E8E8E8; margin: 0.3rem 0;">'
                f'<span style="color: #00A3FF;">⏰</span> {d}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)


def render_hotspot_result(result: Dict[str, Any]):
    """渲染热点分析结果"""
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    hot_topics = result.get("hot_topics", [])
    if hot_topics:
        st.markdown("### 🔥 热门话题")
        for topic in hot_topics:
            st.markdown(
                f'<div class="result-section">'
                f'<div class="result-label">{topic.get("topic", "")} '
                f'<span style="color: #FF9800;">({topic.get("heat", "")})</span></div>'
                f'<div class="result-value">{topic.get("description", "")}</div></div>',
                unsafe_allow_html=True,
            )

    keywords = result.get("keywords", [])
    if keywords:
        st.markdown("### 🔑 高频关键词")
        for kw in keywords:
            freq_color = {"高": "#FF4D4D", "中": "#FFC107", "低": "#00D4AA"}.get(
                kw.get("frequency", ""), "#8892B0"
            )
            st.markdown(
                f'<div style="display: flex; align-items: center; margin: 0.5rem 0; padding: 0.5rem; '
                f'background: rgba(0,0,0,0.2); border-radius: 8px;">'
                f'<span style="font-weight: 600; color: #E8E8E8; min-width: 120px;">{kw.get("word", "")}</span>'
                f'<span style="color: {freq_color}; font-size: 0.85rem; margin: 0 1rem;">'
                f'热度: {kw.get("frequency", "")}</span>'
                f'<span style="color: #8892B0; font-size: 0.85rem;">{kw.get("context", "")}</span></div>',
                unsafe_allow_html=True,
            )

    hot_industries = result.get("hot_industries", [])
    if hot_industries:
        st.markdown("### 🏭 热门行业")
        cols = st.columns(len(hot_industries))
        for i, ind in enumerate(hot_industries):
            with cols[i]:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="result-value" style="font-size: 1rem;">{ind.get("industry", "")}</div>'
                    f'<div class="metric-value">{ind.get("heat_index", 0)}</div>'
                    f'<div class="metric-label">热度指数</div>'
                    f'<div style="color: #8892B0; font-size: 0.75rem; margin-top: 0.5rem;">'
                    f'{ind.get("reason", "")}</div></div>',
                    unsafe_allow_html=True,
                )

    hot_companies = result.get("hot_companies", [])
    if hot_companies:
        st.markdown("### 🏢 热门公司")
        for comp in hot_companies:
            st.markdown(
                f'<div style="display: flex; align-items: center; margin: 0.5rem 0; padding: 0.5rem; '
                f'background: rgba(0,0,0,0.2); border-radius: 8px;">'
                f'<span style="font-weight: 600; color: #CE93D8; min-width: 150px;">{comp.get("company", "")}</span>'
                f'<span style="color: #00D4AA; margin: 0 1rem;">提及 {comp.get("mention_count", 0)} 次</span>'
                f'<span style="color: #8892B0; font-size: 0.85rem;">{comp.get("reason", "")}</span></div>',
                unsafe_allow_html=True,
            )

    sentiment = result.get("market_sentiment", {})
    if sentiment:
        st.markdown("### 📊 市场情绪")
        st.markdown(
            f'<div class="result-section"><div class="result-value">{sentiment.get("overall", "")}</div></div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            bullish = sentiment.get("bullish_factors", [])
            if bullish:
                st.markdown(
                    f'<div class="result-section" style="border-left-color: #00D4AA;">'
                    f'<div class="result-label" style="color: #00D4AA;">📈 看多因素</div>'
                )
                for b in bullish:
                    st.markdown(f'<div class="result-value">• {b}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            bearish = sentiment.get("bearish_factors", [])
            if bearish:
                st.markdown(
                    f'<div class="result-section" style="border-left-color: #FF4D4D;">'
                    f'<div class="result-label" style="color: #FF4D4D;">📉 看空因素</div>'
                )
                for b in bearish:
                    st.markdown(f'<div class="result-value">• {b}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    trend = result.get("trend_analysis", "")
    if trend:
        st.markdown("### 🔮 趋势判断")
        st.markdown(
            f'<div class="result-section" style="border-left-color: #00A3FF;">'
            f'<div class="result-value">{trend}</div></div>',
            unsafe_allow_html=True,
        )

    attention = result.get("attention_areas", [])
    if attention:
        st.markdown("### 👀 值得关注的领域")
        tags = "".join(f'<span class="tag tag-industry">{area}</span>' for area in attention)
        st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 股票深度解码结果渲染
# ============================================================
def render_stock_decode_result(result: Dict[str, Any]):
    """渲染股票深度解码分析结果"""
    # 结构完整性校验
    required_parts = ["part1_market_identity", "part2_price_action", "part3_drivers_sentiment", "part4_outlook_strategy"]
    missing_parts = [p for p in required_parts if p not in result]
    if missing_parts:
        st.warning(f"⚠️ 分析结果部分缺失: {', '.join(missing_parts)}，显示已有内容")

    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    # ===== 第一部分：股票身份与跨境监管透视 =====
    part1 = result.get("part1_market_identity", {})
    if part1 and isinstance(part1, dict):
        st.markdown("## 🔍 第一部分：股票身份与跨境监管透视")
        st.markdown("---")

        market = part1.get("market_judgment", {})
        if market:
            st.markdown("### 🔹 基本信息")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="result-section">'
                    f'<div class="result-label">所属市场</div>'
                    f'<div class="result-value"><b>{market.get("market", "未知")}</b></div>'
                    f'<div style="color:#8892B0;font-size:0.85rem;margin-top:0.3rem;">{market.get("reason", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="result-section">'
                    f'<div class="result-label">交易所</div>'
                    f'<div class="result-value"><b>{market.get("exchange", "未知")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="result-section">'
                    f'<div class="result-label">监管机构</div>'
                    f'<div class="result-value"><b>{market.get("regulator", "未知")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="result-section">'
                    f'<div class="result-label">上市公司</div>'
                    f'<div class="result-value">{market.get("stock_name", "未知")}</div>'
                    f'<div style="color:#8892B0;font-size:0.85rem;margin-top:0.3rem;">{market.get("business_sector", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        rules = part1.get("trading_rules", {})
        if rules:
            st.markdown("### 🔹 监管合规与交易机制")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">结算方式</div>'
                    f'<div class="result-value" style="font-size:1.2rem;"><b>{rules.get("settlement", "未知")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">涨跌幅限制</div>'
                    f'<div class="result-value" style="font-size:1rem;">{rules.get("price_limit", "未知")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">融券做空</div>'
                    f'<div class="result-value" style="font-size:1rem;">{rules.get("short_selling", "未知")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        thresholds = part1.get("abnormal_thresholds", {})
        if thresholds:
            st.markdown("### 🔹 异动公告触发临界点")
            st.markdown(
                f'<div class="result-section" style="border-left-color:#FF4D4D;">'
                f'<div class="result-label">规则说明</div>'
                f'<div class="result-value">{thresholds.get("rule_description", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for key in ["a_share_mainboard", "chi_next", "other_rules"]:
                val = thresholds.get(key, "")
                if val:
                    st.markdown(
                        f'<div style="margin:0.5rem 0;padding:0.5rem;background:rgba(255,77,77,0.05);'
                        f'border-radius:8px;color:#E8E8E8;">⚠️ {val}</div>',
                        unsafe_allow_html=True,
                    )

    # ===== 第二部分：盘面异动与资金行为推演 =====
    part2 = result.get("part2_price_action", {})
    if part2:
        st.markdown("## 📊 第二部分：盘面异动与资金行为推演")
        st.markdown("---")

        st.markdown(
            f'<div class="result-section">'
            f'<div class="result-label">异动状态评估</div>'
            f'<div class="result-value">{part2.get("abnormal_assessment", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="result-section" style="border-left-color:#00A3FF;">'
            f'<div class="result-label">资金行为推演</div>'
            f'<div class="result-value">{part2.get("capital_flow_analysis", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="result-section" style="border-left-color:#FF9800;">'
            f'<div class="result-label">盘中急涨急跌异动</div>'
            f'<div class="result-value">{part2.get("intraday_anomaly", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ===== 第三部分：核心驱动力与舆情情绪拆解 =====
    part3 = result.get("part3_drivers_sentiment", {})
    if part3:
        st.markdown("## 💣 第三部分：核心驱动力与舆情情绪拆解")
        st.markdown("---")

        drivers = part3.get("driver_types", {})
        if drivers:
            st.markdown("### 🔹 驱动力分类")
            for d_key, d_val in drivers.items():
                icons = {"fundamental": "📊", "policy": "🏛️", "sentiment": "🔥"}
                labels = {"fundamental": "基本面驱动", "policy": "政策周期驱动", "sentiment": "情绪题材驱动"}
                st.markdown(
                    f'<div class="result-section">'
                    f'<div class="result-label">{icons.get(d_key, "📌")} {labels.get(d_key, d_key)}</div>'
                    f'<div class="result-value">{d_val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        sentiment = part3.get("market_sentiment", {})
        if sentiment:
            st.markdown("### 🔹 市场情绪量化模拟")
            st.markdown(
                f'<div class="result-section" style="border-left-color:#FFC107;">'
                f'<div class="result-label">整体情绪</div>'
                f'<div class="result-value"><b>{sentiment.get("overall", "")}</b></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            risk = sentiment.get("risk_warning", "")
            if risk:
                st.markdown(
                    f'<div class="result-section" style="border-left-color:#FF4D4D;">'
                    f'<div class="result-label" style="color:#FF4D4D;">⚠️ 风险警告</div>'
                    f'<div class="result-value">{risk}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ===== 第四部分：空间博弈与多空展望 =====
    part4 = result.get("part4_outlook_strategy", {})
    if part4:
        st.markdown("## 🚀 第四部分：空间博弈与多空展望")
        st.markdown("---")

        tech = part4.get("technical_levels", {})
        if tech:
            st.markdown("### 🔹 技术面心理位")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="result-section" style="border-left-color:#00D4AA;">'
                    f'<div class="result-label">🛡️ 心理支撑位</div>'
                    f'<div class="result-value"><b>{tech.get("support", "待分析")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="result-section" style="border-left-color:#FF4D4D;">'
                    f'<div class="result-label">🚧 上行阻力位</div>'
                    f'<div class="result-value"><b>{tech.get("resistance", "待分析")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        rr = part4.get("risk_reward_ratio", {})
        if rr:
            st.markdown("### 🔹 涨跌幅空间评估（风险收益比）")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">📈 上行空间</div>'
                    f'<div class="result-value" style="font-size:1rem;">{rr.get("upside_space", "待评估")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">📉 下行风险</div>'
                    f'<div class="result-value" style="font-size:1rem;color:#FF4D4D;">{rr.get("downside_space", "待评估")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">⚖️ 风险收益比</div>'
                    f'<div class="result-value" style="font-size:1rem;color:#FFC107;"><b>{rr.get("ratio", "待评估")}</b></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        strategy = part4.get("strategy_advice", {})
        if strategy:
            st.markdown("### 🔹 操盘策略建议")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="result-section" style="border-left-color:#00D4AA;">'
                    f'<div class="result-label">⚡ 短线趋势交易者</div>'
                    f'<div class="result-value">{strategy.get("short_term", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="result-section" style="border-left-color:#00A3FF;">'
                    f'<div class="result-label">💎 中线价值投资者</div>'
                    f'<div class="result-value">{strategy.get("mid_term", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ===== 免责声明 =====
    disclaimer = result.get("disclaimer", "")
    if disclaimer:
        st.markdown("---")
        st.markdown(
            f'<div style="background:rgba(255,152,0,0.1);border:1px solid rgba(255,152,0,0.3);'
            f'border-radius:8px;padding:1rem;margin-top:1rem;">'
            f'<div style="color:#FF9800;font-weight:600;margin-bottom:0.5rem;">⚠️ 免责声明</div>'
            f'<div style="color:#E8E8E8;font-size:0.85rem;">{disclaimer}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 功能页面
# ============================================================
def render_news_analysis_page():
    """财经新闻分析页面"""
    st.markdown('<div class="app-header">📰 财经新闻分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">输入财经新闻，AI 自动分析总结、利好利空判断、风险提示</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ 请先在左侧边栏配置并连接 API")
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    news_text = st.text_area(
        "📝 输入财经新闻内容",
        height=200,
        placeholder="请粘贴或输入财经新闻内容...\n\n例如：中国人民银行宣布下调存款准备金率0.5个百分点...",
        key="news_input",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button("🚀 开始分析", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_btn and news_text.strip():
        with st.spinner("🔄 AI 正在分析财经新闻..."):
            try:
                prompt = PromptManager.get_prompt("news_analysis")
                result_text = st.session_state.api_client.analyze_financial_news(
                    news_text.strip(), prompt
                )
                result = parse_json_response(result_text)

                # 保存到历史
                st.session_state.analysis_history.append({
                    "type": "news_analysis",
                    "input": news_text.strip()[:100] + "...",
                    "result": result,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

                render_analysis_result(result, "news_analysis")

            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")

    elif analyze_btn:
        st.warning("⚠️ 请输入财经新闻内容")


def render_announcement_analysis_page():
    """上市公司公告分析页面"""
    st.markdown('<div class="app-header">📋 上市公司公告分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">输入公告内容，AI 提取核心事件、财务数据和风险提示</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ 请先在左侧边栏配置并连接 API")
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    announcement_text = st.text_area(
        "📝 输入公告内容",
        height=200,
        placeholder="请粘贴或输入上市公司公告内容...\n\n例如：XX股份有限公司2024年度业绩预告...",
        key="announcement_input",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button("🚀 开始分析", use_container_width=True, key="ann_btn")
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_btn and announcement_text.strip():
        with st.spinner("🔄 AI 正在分析公告..."):
            try:
                prompt = PromptManager.get_prompt("announcement_analysis")
                result_text = st.session_state.api_client.analyze_announcement(
                    announcement_text.strip(), prompt
                )
                result = parse_json_response(result_text)

                st.session_state.analysis_history.append({
                    "type": "announcement_analysis",
                    "input": announcement_text.strip()[:100] + "...",
                    "result": result,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

                render_analysis_result(result, "announcement_analysis")

            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")

    elif analyze_btn:
        st.warning("⚠️ 请输入公告内容")


def render_hotspot_analysis_page():
    """市场热点分析页面"""
    st.markdown('<div class="app-header">🔥 市场热点分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">输入多条财经新闻，AI 提取市场热点、热门行业和公司</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ 请先在左侧边栏配置并连接 API")
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    news_list = st.text_area(
        "📝 输入多条财经新闻（每条一行或分段）",
        height=200,
        placeholder="请粘贴多条财经新闻，每条新闻用换行分隔...\n\n"
                    "新闻1：某科技公司发布新一代AI芯片...\n"
                    "新闻2：新能源车企公布月度销量数据...\n"
                    "新闻3：央行发布最新货币政策报告...",
        key="hotspot_input",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button("🚀 开始分析", use_container_width=True, key="hot_btn")
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_btn and news_list.strip():
        with st.spinner("🔄 AI 正在分析市场热点..."):
            try:
                prompt = PromptManager.get_prompt("hotspot_analysis")
                result_text = st.session_state.api_client.analyze_hotspots(
                    news_list.strip(), prompt
                )
                result = parse_json_response(result_text)

                st.session_state.analysis_history.append({
                    "type": "hotspot_analysis",
                    "input": news_list.strip()[:100] + "...",
                    "result": result,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

                render_analysis_result(result, "hotspot_analysis")

            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")

    elif analyze_btn:
        st.warning("⚠️ 请输入新闻内容")


def render_stock_decode_page():
    """股票深度解码页面"""
    st.markdown('<div class="app-header">🔍 股票深度解码</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">CFA 级专业分析 — 输入股票代码或名称，获取多维度深度解码</div>',
        unsafe_allow_html=True,
    )

    # 输入区域
    st.markdown("### 📌 股票查询")
    stock_input = st.text_input(
        "输入股票名称或代码（如：贵州茅台、600519、AAPL、TSLA）",
        placeholder="例：贵州茅台 / 600519 / AAPL / 0700.HK",
        key="stock_decode_input",
    )

    # 分析按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button(
            "🔍 开始深度解码",
            type="primary",
            use_container_width=True,
        )

    if analyze_btn and stock_input:
        with st.spinner("🔄 AI 正在深度分析，请稍候..."):
            try:
                if not st.session_state.api_client:
                    st.error("⚠️ 请先在侧边栏配置 API 密钥")
                    return
                prompt_template = PromptManager.get_prompt("stock_deep_decode")
                result_text = st.session_state.api_client.analyze_stock_deep_decode(
                    stock_input, prompt_template
                )
                result = parse_json_response(result_text)

                if "error" in result:
                    st.error(f"❌ 分析失败: {result['error']}")
                    if "raw_content" in result:
                        with st.expander("查看原始返回内容"):
                            st.text(result["raw_content"])
                else:
                    # 保存历史
                    st.session_state.analysis_history.append({
                        "type": "stock_deep_decode",
                        "input": stock_input,
                        "result": result,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

                    render_stock_decode_result(result)

            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")

    elif analyze_btn:
        st.warning("⚠️ 请输入股票名称或代码")


def render_history_page():
    """历史记录页面"""
    st.markdown('<div class="app-header">📚 分析历史</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">查看本次会话的所有分析记录</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.analysis_history:
        st.markdown(
            '<div class="card" style="text-align: center; padding: 3rem;">'
            '<div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>'
            '<div style="color: #8892B0;">暂无分析记录</div>'
            '<div style="color: #4A4D5E; font-size: 0.85rem; margin-top: 0.5rem;">'
            '使用上方功能模块进行分析后，记录将显示在这里</div></div>',
            unsafe_allow_html=True,
        )
        return

    for i, record in enumerate(reversed(st.session_state.analysis_history)):
        type_icons = {
            "news_analysis": "📰",
            "announcement_analysis": "📋",
            "hotspot_analysis": "🔥",
            "stock_deep_decode": "🔍",
        }
        icon = type_icons.get(record["type"], "📄")

        with st.expander(f"{icon} {record['time']} - {record['input']}"):
            render_analysis_result(record["result"], record["type"])


# ============================================================
# 主函数
# ============================================================
def main():
    """应用主入口"""
    # 初始化
    init_session_state()
    load_css()

    # 渲染侧边栏
    render_sidebar()

    # 主内容区域
    st.markdown(
        '<div class="app-header">📈 AI 金融信息分析助手</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="app-subtitle">AI Financial Insight Assistant — 智能分析，洞见未来</div>',
        unsafe_allow_html=True,
    )

    # 根据当前页面渲染对应功能
    page_handlers = {
        "news_analysis": render_news_analysis_page,
        "announcement_analysis": render_announcement_analysis_page,
        "hotspot_analysis": render_hotspot_analysis_page,
        "stock_deep_decode": render_stock_decode_page,
    }

    handler = page_handlers.get(st.session_state.current_page)
    if handler:
        handler()

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <div>📈 AI 金融信息分析助手 | AI Financial Insight Assistant</div>
        <div style="margin-top: 0.5rem;">
            免责声明：本工具提供的分析仅供参考，不构成投资建议。投资有风险，决策需谨慎。
        </div>
        <div style="margin-top: 0.25rem; color: #3A3D4E;">
            Powered by Streamlit + AI API | 数据来源：用户输入
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()