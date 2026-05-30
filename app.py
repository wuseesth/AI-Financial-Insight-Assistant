"""
AI 金融信息分析助手 (AI Financial Insight Assistant)
==================================================
主入口文件 - Streamlit 多页面应用

功能模块：
1. 📰 财经新闻分析 - 自动总结、利好利空分析
2. 📋 上市公司公告分析 - 核心事件提取、财务数据分析
3. 🔥 市场热点分析 - 热点话题、热门行业/公司提取
4. 🔍 股票深度解码 - 机构级多维度深度解码（评分卡、技术面、资金面、风险收益、策略建议）
5. 📊 多股票对比分析 - 跨市场横向对比

技术栈：Python + Streamlit + DeepSeek/OpenAI API
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# 项目内部模块
from services.api_client import APIClient, get_available_backends, get_backend_models
from services.market_data import MarketDataService
from services.report_export import ReportExporter
from services.technical_indicators import TechnicalIndicators
from services.realtime_market_data import RealtimeMarketDataService
from services.scoring_engine import ScoringEngine
from prompts.financial_prompts import PromptManager
from utils.helpers import parse_json_response
from utils.config import AppConfig

# Plotly 可视化
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ============================================================
# 页面配置（必须在第一个 st 命令之前）
# ============================================================
st.set_page_config(**AppConfig.PAGE_CONFIG)

# ============================================================
# 自定义 CSS - 金融科技深色主题
# ============================================================
def load_css():
    """加载自定义 CSS 样式 — 企业级金融终端主题（无外部依赖，中国网络友好）"""
    st.markdown("""
    <style>
        /* ===== 字体系统（纯本地，无 Google Fonts 依赖） ===== */
        * {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                         'Microsoft YaHei', 'Noto Sans SC', 'Helvetica Neue', Arial, sans-serif;
        }
        code, pre, .mono, .metric-value, .pro-table, .pro-rating-scale {
            font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace !important;
        }

        /* ===== 基础布局 ===== */
        .stApp {
            background: #131722;
        }
        .stApp > header {
            display: none !important;
        }
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            max-width: 1200px !important;
        }

        /* ===== 滚动条 ===== */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2A2D3E; border-radius: 2px; }

        /* ===== 顶部导航栏 ===== */
        .topbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0.35rem 0; margin-bottom: 0.6rem;
            border-bottom: 1px solid rgba(42,45,62,0.4);
        }
        .topbar-brand { display: flex; align-items: center; gap: 0.5rem; }
        .topbar-logo {
            width: 26px; height: 26px;
            background: linear-gradient(135deg, #00D4AA, #00A3FF);
            border-radius: 5px;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.8rem; font-weight: 800; color: #131722;
        }
        .topbar-title { font-size: 0.9rem; font-weight: 700; color: #D1D4DC; letter-spacing: 0.3px; }
        .topbar-title span { color: #00D4AA; }
        .topbar-version {
            font-size: 0.55rem; color: #5D6070;
            background: rgba(42,45,62,0.4); padding: 0.08rem 0.35rem;
            border-radius: 3px; margin-left: 0.35rem;
        }
        .topbar-status { display: flex; align-items: center; gap: 0.6rem; font-size: 0.65rem; color: #5D6070; }
        .status-dot {
            width: 5px; height: 5px; border-radius: 50%; display: inline-block; margin-right: 3px;
        }
        .status-dot.online { background: #00D4AA; box-shadow: 0 0 4px rgba(0,212,170,0.5); }
        .status-dot.offline { background: #FF4D4D; }

        /* ===== 页面标题 ===== */
        .page-header {
            font-size: 1.25rem; font-weight: 700; color: #D1D4DC;
            margin-bottom: 0.1rem; letter-spacing: -0.3px;
        }
        .page-subtitle {
            font-size: 0.72rem; color: #5D6070; margin-bottom: 0.8rem;
        }

        /* ===== 卡片系统 ===== */
        .card {
            background: #1A1D28; border: 1px solid #252836;
            border-radius: 6px; padding: 0.7rem; margin-bottom: 0.45rem;
        }
        .card-header {
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 0.4rem; padding-bottom: 0.35rem;
            border-bottom: 1px solid rgba(42,45,62,0.25);
        }
        .card-title {
            font-size: 0.62rem; font-weight: 600; color: #5D6070;
            text-transform: uppercase; letter-spacing: 0.8px;
        }
        .card-body {
            font-size: 0.78rem; color: #B0B4C0; line-height: 1.5;
        }

        /* ===== 数据行 ===== */
        .data-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.22rem 0; border-bottom: 1px solid rgba(42,45,62,0.12);
        }
        .data-row:last-child { border-bottom: none; }
        .data-label { font-size: 0.68rem; color: #5D6070; }
        .data-value { font-size: 0.72rem; color: #B0B4C0; font-weight: 500; }
        .data-value.up { color: #00D4AA; }
        .data-value.down { color: #FF4D4D; }
        .data-value.neutral { color: #FFC107; }

        /* ===== 标签 ===== */
        .tag {
            display: inline-block; padding: 0.08rem 0.35rem;
            border-radius: 2px; font-size: 0.58rem; font-weight: 600; letter-spacing: 0.2px;
        }
        .tag-bullish { background: rgba(0,212,170,0.1); color: #00D4AA; }
        .tag-bearish { background: rgba(255,77,77,0.1); color: #FF4D4D; }
        .tag-neutral { background: rgba(255,193,7,0.1); color: #FFC107; }
        .tag-industry { background: rgba(0,163,255,0.1); color: #00A3FF; }
        .tag-company { background: rgba(156,39,176,0.1); color: #CE93D8; }
        .tag-risk { background: rgba(255,152,0,0.1); color: #FF9800; }

        /* ===== 指标网格 ===== */
        .metric-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 0.35rem; margin-bottom: 0.45rem;
        }
        .metric-item {
            background: rgba(0,0,0,0.2); border: 1px solid rgba(42,45,62,0.25);
            border-radius: 4px; padding: 0.45rem; text-align: center;
        }
        .metric-value {
            font-size: 0.95rem; font-weight: 700; color: #D1D4DC;
        }
        .metric-value.up { color: #00D4AA; }
        .metric-value.down { color: #FF4D4D; }
        .metric-label {
            font-size: 0.52rem; color: #5D6070;
            text-transform: uppercase; letter-spacing: 0.4px; margin-top: 0.12rem;
        }

        /* ===== Streamlit 组件覆盖 ===== */
        .stButton > button {
            background: #00D4AA !important; color: #131722 !important;
            border: none !important; border-radius: 4px !important;
            padding: 0.25rem 0.9rem !important; font-size: 0.72rem !important;
            font-weight: 600 !important; height: auto !important;
            transition: all 0.12s !important;
        }
        .stButton > button:hover {
            background: #00E6B5 !important;
            box-shadow: 0 2px 8px rgba(0,212,170,0.25) !important;
        }
        .stButton > button:active { transform: scale(0.97); }

        .stTextInput > div > div > input,
        .stTextArea textarea {
            background: #1A1D28 !important; border: 1px solid #252836 !important;
            border-radius: 4px !important; color: #B0B4C0 !important;
            font-size: 0.78rem !important; padding: 0.35rem 0.55rem !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea textarea:focus {
            border-color: #00D4AA !important;
            box-shadow: 0 0 0 1px rgba(0,212,170,0.15) !important;
        }

        .stSelectbox > div > div {
            background: #1A1D28 !important; border: 1px solid #252836 !important;
            border-radius: 4px !important; color: #B0B4C0 !important;
            font-size: 0.72rem !important; min-height: 28px !important;
        }
        /* 下拉菜单选项 */
        div[data-baseweb="select"] > div {
            background: #1A1D28 !important;
        }
        div[data-baseweb="select"] ul {
            background: #1A1D28 !important;
        }
        div[data-baseweb="select"] li {
            color: #B0B4C0 !important;
        }
        div[data-baseweb="select"] li:hover {
            background: rgba(0,212,170,0.08) !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0; background: transparent;
            border-bottom: 1px solid #252836; padding: 0; border-radius: 0;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 0 !important; padding: 0.35rem 0.75rem !important;
            color: #5D6070 !important; font-size: 0.72rem !important;
            border-bottom: 2px solid transparent !important;
            transition: all 0.12s !important;
        }
        .stTabs [aria-selected="true"] {
            color: #00D4AA !important;
            border-bottom-color: #00D4AA !important;
            background: transparent !important;
        }
        .stTabs [data-baseweb="tab"]:hover { color: #8892B0 !important; }

        .stProgress > div > div { background: #00D4AA !important; }
        hr { border-color: #252836 !important; margin: 0.6rem 0 !important; }

        /* ===== Streamlit 侧边栏覆盖 ===== */
        section[data-testid="stSidebar"] {
            background: #131722 !important;
            border-right: 1px solid #252836 !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            width: 100% !important;
            background: transparent !important;
            color: #B0B4C0 !important;
            border: 1px solid #252836 !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 0.35rem 0.6rem !important;
            font-size: 0.72rem !important;
            font-weight: 500 !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(0,212,170,0.06) !important;
            border-color: rgba(0,212,170,0.2) !important;
            color: #00D4AA !important;
        }
        section[data-testid="stSidebar"] .stButton > button:focus {
            box-shadow: none !important;
        }

        /* ===== 侧边栏品牌样式 ===== */
        .sidebar-brand {
            text-align: center; padding: 0.4rem 0;
        }
        .sidebar-logo {
            width: 30px; height: 30px; margin: 0 auto 0.35rem;
            background: linear-gradient(135deg, #00D4AA, #00A3FF);
            border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.85rem; font-weight: 800; color: #131722;
        }
        .sidebar-title {
            font-size: 0.85rem; font-weight: 700; color: #D1D4DC; letter-spacing: 0.3px;
        }
        .sidebar-version {
            font-size: 0.55rem; color: #5D6070; margin-top: 0.12rem;
        }
        .sidebar-divider {
            height: 1px; background: rgba(42,45,62,0.3); margin: 0.4rem 0;
        }
        .sidebar-section-title {
            color: #5D6070; font-weight: 600; font-size: 0.65rem;
            margin-bottom: 0.35rem; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .sidebar-status {
            background: rgba(0,212,170,0.06); border: 1px solid rgba(0,212,170,0.12);
            border-radius: 4px; padding: 0.3rem 0.55rem; margin: 0.4rem 0;
        }
        .sidebar-status-dot {
            display: inline-block; width: 5px; height: 5px; border-radius: 50%;
            background: #00D4AA; box-shadow: 0 0 4px rgba(0,212,170,0.5); margin-right: 4px;
        }
        .sidebar-status-text {
            color: #00D4AA; font-size: 0.72rem; font-weight: 600;
        }
        .sidebar-status-sub {
            color: #5D6070; font-size: 0.62rem;
        }
        .sidebar-stats {
            color: #5D6070; font-size: 0.72rem; text-align: center;
        }
        .sidebar-stats-count {
            color: #00D4AA; font-weight: 700;
        }
        .sidebar-footer {
            text-align: center; color: #2A2D3E; font-size: 0.58rem; padding: 0.4rem 0;
        }

        /* ===== 机构级股票深度解码样式 ===== */
        .pro-scorecard {
            background: linear-gradient(145deg, #1A1D28, #1E212E);
            border: 1px solid #252836;
            border-radius: 6px;
            padding: 0.7rem;
            margin: 0.45rem 0;
        }
        .pro-rating-badge {
            display: inline-block;
            padding: 0.22rem 0.7rem;
            border-radius: 4px;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        /* ===== 评级徽章 ===== */
        .pro-rating-strong-buy { background: linear-gradient(135deg, #00D4AA, #00A3FF); color: #fff; }
        .pro-rating-buy { background: rgba(0, 212, 170, 0.2); color: #00D4AA; border: 1px solid #00D4AA; }
        .pro-rating-hold { background: rgba(255, 193, 7, 0.2); color: #FFC107; border: 1px solid #FFC107; }
        .pro-rating-avoid { background: rgba(255, 77, 77, 0.2); color: #FF4D4D; border: 1px solid #FF4D4D; }
        .pro-rating-strong-sell { background: linear-gradient(135deg, #FF4D4D, #D32F2F); color: #fff; }

        /* ===== 维度评分条 ===== */
        .pro-dimension-bar {
            height: 4px; border-radius: 2px; margin-top: 3px;
            transition: width 0.5s ease;
        }
        .pro-dimension-label {
            font-size: 0.62rem; color: #5D6070;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .pro-dimension-score {
            font-size: 0.78rem; font-weight: 700;
        }

        /* ===== 章节标题 ===== */
        .pro-section-header {
            font-size: 0.72rem; font-weight: 700;
            padding: 0.3rem 0.55rem;
            border-radius: 4px;
            margin: 0.45rem 0 0.35rem 0;
            cursor: pointer; user-select: none;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .pro-section-header-buy { background: rgba(0, 212, 170, 0.08); border-left: 3px solid #00D4AA; color: #00D4AA; }
        .pro-section-header-sell { background: rgba(255, 77, 77, 0.08); border-left: 3px solid #FF4D4D; color: #FF4D4D; }
        .pro-section-header-neutral { background: rgba(255, 193, 7, 0.08); border-left: 3px solid #FFC107; color: #FFC107; }
        .pro-section-header-info { background: rgba(0, 163, 255, 0.08); border-left: 3px solid #00A3FF; color: #00A3FF; }

        /* ===== 数据行 ===== */
        .pro-data-row {
            display: flex; justify-content: space-between;
            padding: 0.22rem 0;
            border-bottom: 1px solid rgba(42, 45, 62, 0.3);
        }
        .pro-data-label { color: #5D6070; font-size: 0.68rem; }
        .pro-data-value { color: #B0B4C0; font-size: 0.72rem; font-weight: 600; }
        .pro-data-value-up { color: #00D4AA; }
        .pro-data-value-down { color: #FF4D4D; }

        /* ===== 信号指示 ===== */
        .pro-signal-bullish { color: #00D4AA; font-weight: 600; font-size: 0.72rem; }
        .pro-signal-bearish { color: #FF4D4D; font-weight: 600; font-size: 0.72rem; }
        .pro-signal-neutral { color: #FFC107; font-weight: 600; font-size: 0.72rem; }

        /* ===== 风险标签 ===== */
        .pro-risk-tag {
            display: inline-block;
            padding: 0.08rem 0.35rem;
            border-radius: 3px;
            font-size: 0.62rem;
            font-weight: 600;
            margin: 0.08rem;
        }
        .pro-risk-high { background: rgba(255, 77, 77, 0.12); color: #FF4D4D; border: 1px solid rgba(255, 77, 77, 0.25); }
        .pro-risk-mid { background: rgba(255, 193, 7, 0.12); color: #FFC107; border: 1px solid rgba(255, 193, 7, 0.25); }
        .pro-risk-low { background: rgba(0, 212, 170, 0.12); color: #00D4AA; border: 1px solid rgba(0, 212, 170, 0.25); }

        /* ===== 价位卡片 ===== */
        .pro-level-card {
            background: rgba(0, 0, 0, 0.15);
            border-radius: 4px;
            padding: 0.45rem;
            text-align: center;
            border: 1px solid rgba(42, 45, 62, 0.3);
        }
        .pro-level-support { border-top: 2px solid #00D4AA; }
        .pro-level-resistance { border-top: 2px solid #FF4D4D; }
        .pro-level-stop { border-top: 2px solid #FF9800; }

        /* ===== 情景卡片 ===== */
        .pro-scenario-card {
            background: rgba(0, 0, 0, 0.15);
            border-radius: 4px;
            padding: 0.55rem;
            border: 1px solid rgba(42, 45, 62, 0.3);
            height: 100%;
        }
        .pro-scenario-bull { border-top: 2px solid #00D4AA; }
        .pro-scenario-bear { border-top: 2px solid #FF4D4D; }
        .pro-scenario-base { border-top: 2px solid #FFC107; }

        /* ===== 快速选择栏 ===== */
        .pro-ticker-bar {
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(42, 45, 62, 0.3);
            border-radius: 4px;
            padding: 0.35rem 0.55rem;
            margin-bottom: 0.45rem;
        }

        /* ===== 信号指示灯 ===== */
        .signal-dot {
            display: inline-block;
            width: 6px; height: 6px;
            border-radius: 50%;
            margin-right: 4px;
        }
        .signal-dot-green { background: #00D4AA; box-shadow: 0 0 4px rgba(0, 212, 170, 0.4); }
        .signal-dot-red { background: #FF4D4D; box-shadow: 0 0 4px rgba(255, 77, 77, 0.4); }
        .signal-dot-yellow { background: #FFC107; box-shadow: 0 0 4px rgba(255, 193, 7, 0.4); }

        /* ===== 专业表格 ===== */
        .pro-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.68rem;
        }
        .pro-table th {
            background: rgba(0, 212, 170, 0.06);
            color: #00D4AA;
            padding: 0.28rem 0.38rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid rgba(0, 212, 170, 0.15);
        }
        .pro-table td {
            padding: 0.22rem 0.38rem;
            border-bottom: 1px solid rgba(42, 45, 62, 0.3);
            color: #B0B4C0;
        }
        .pro-table tr:hover td {
            background: rgba(0, 212, 170, 0.02);
        }

        /* ===== 评级刻度表 ===== */
        .pro-rating-scale {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.62rem;
            margin: 0.25rem 0;
        }
        .pro-rating-scale th {
            background: rgba(0, 212, 170, 0.06);
            color: #00D4AA;
            padding: 0.22rem 0.38rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.58rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid rgba(0, 212, 170, 0.12);
        }
        .pro-rating-scale td {
            padding: 0.18rem 0.38rem;
            border-bottom: 1px solid rgba(42, 45, 62, 0.2);
            color: #8892B0;
            vertical-align: top;
        }
        .pro-rating-scale tr:hover td {
            background: rgba(0, 212, 170, 0.02);
        }
        .pro-rating-scale .scale-indicator {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 2px;
            margin-right: 4px;
            vertical-align: middle;
        }
        .pro-rating-scale .scale-range {
            font-weight: 700;
            font-size: 0.68rem;
        }
        .pro-rating-scale .scale-rating {
            font-weight: 600;
        }
        .pro-rating-scale .scale-meaning {
            color: #5D6070;
            font-size: 0.58rem;
            line-height: 1.3;
        }
        .pro-rating-scale .scale-action {
            font-size: 0.58rem;
            font-weight: 600;
        }
        .pro-rating-scale .active-row td {
            background: rgba(0, 212, 170, 0.06) !important;
            border-left: 2px solid #00D4AA;
        }

        /* ===== 评分详情面板 ===== */
        .pro-scoring-detail {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            padding: 0.45rem 0.55rem;
            margin: 0.18rem 0 0.35rem 0;
            border-left: 2px solid rgba(0, 212, 170, 0.25);
        }
        .pro-scoring-detail-label {
            color: #00D4AA;
            font-size: 0.58rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.18rem;
        }
        .pro-scoring-detail-text {
            color: #5D6070;
            font-size: 0.65rem;
            line-height: 1.4;
        }
        .pro-scoring-summary-box {
            background: rgba(0, 212, 170, 0.04);
            border: 1px solid rgba(0, 212, 170, 0.12);
            border-radius: 4px;
            padding: 0.45rem 0.55rem;
            margin: 0.35rem 0;
        }
        .pro-scoring-summary-label {
            color: #00D4AA;
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.25rem;
        }
        .pro-scoring-summary-text {
            color: #5D6070;
            font-size: 0.68rem;
            line-height: 1.5;
        }
        .pro-scoring-toggle {
            color: #00A3FF;
            font-size: 0.62rem;
            cursor: pointer;
            user-select: none;
            padding: 0.12rem 0.35rem;
            border-radius: 3px;
            background: rgba(0, 163, 255, 0.08);
            display: inline-block;
            transition: all 0.2s;
        }
        .pro-scoring-toggle:hover {
            background: rgba(0, 163, 255, 0.15);
        }
        .pro-scoring-criteria-box {
            background: rgba(255, 193, 7, 0.04);
            border: 1px solid rgba(255, 193, 7, 0.12);
            border-radius: 4px;
            padding: 0.35rem 0.55rem;
            margin: 0.18rem 0;
        }
        .pro-scoring-criteria-label {
            color: #FFC107;
            font-size: 0.58rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .pro-scoring-criteria-text {
            color: #5D6070;
            font-size: 0.62rem;
            line-height: 1.4;
        }
        .pro-data-source-box {
            background: rgba(0, 163, 255, 0.04);
            border: 1px solid rgba(0, 163, 255, 0.12);
            border-radius: 4px;
            padding: 0.35rem 0.55rem;
            margin: 0.18rem 0;
        }
        .pro-data-source-label {
            color: #00A3FF;
            font-size: 0.58rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .pro-data-source-text {
            color: #5D6070;
            font-size: 0.62rem;
            line-height: 1.4;
        }

        /* ===== 输入框 ===== */
        .pro-input {
            background: #1A1D28 !important;
            border: 1px solid #252836 !important;
            border-radius: 4px !important;
            color: #B0B4C0 !important;
            font-size: 0.82rem !important;
            padding: 0.45rem 0.55rem !important;
        }
        .pro-input:focus {
            border-color: #00D4AA !important;
            box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1) !important;
        }

        /* ===== 市场标签 ===== */
        .pro-market-tag {
            display: inline-block;
            padding: 0.08rem 0.32rem;
            border-radius: 3px;
            font-size: 0.58rem;
            font-weight: 600;
            margin-left: 0.18rem;
        }
        .pro-market-a { background: rgba(255, 77, 77, 0.15); color: #FF4D4D; }
        .pro-market-hk { background: rgba(255, 193, 7, 0.15); color: #FFC107; }
        .pro-market-us { background: rgba(0, 163, 255, 0.15); color: #00A3FF; }

        /* ===== 快速选择按钮 ===== */
        .pro-quick-btn {
            background: rgba(42, 45, 62, 0.3) !important;
            border: 1px solid rgba(42, 45, 62, 0.5) !important;
            color: #5D6070 !important;
            border-radius: 3px !important;
            padding: 0.12rem 0.45rem !important;
            font-size: 0.62rem !important;
            font-weight: 500 !important;
            transition: all 0.15s !important;
        }
        .pro-quick-btn:hover {
            background: rgba(0, 212, 170, 0.12) !important;
            color: #00D4AA !important;
            border-color: rgba(0, 212, 170, 0.3) !important;
        }

        /* ===== 技术指标卡片 ===== */
        .pro-indicator-card {
            background: rgba(0, 0, 0, 0.15);
            border-radius: 4px;
            padding: 0.35rem;
            text-align: center;
            border: 1px solid rgba(42, 45, 62, 0.3);
        }
        .pro-indicator-value {
            font-size: 0.95rem;
            font-weight: 700;
        }
        .pro-indicator-label {
            font-size: 0.58rem;
            color: #5D6070;
            margin-top: 0.12rem;
        }

        /* ===== 信号强度条 ===== */
        .pro-signal-bar {
            height: 3px;
            border-radius: 2px;
            margin-top: 0.18rem;
            transition: width 0.5s ease;
        }

        /* ===== 页脚 ===== */
        .app-footer {
            text-align: center;
            color: #2A2D3E;
            font-size: 0.62rem;
            padding: 0.45rem 0;
            line-height: 1.6;
        }
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
        "current_page": "stock_deep_decode",
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
        <div class="sidebar-brand">
            <div class="sidebar-logo">AI</div>
            <div class="sidebar-title">Financial Insight</div>
            <div class="sidebar-version">v2.0.0</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # API 配置区域
        st.markdown('<div class="sidebar-section-title">🔑 API 配置</div>', unsafe_allow_html=True)

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
            <div class="sidebar-status">
                <span class="sidebar-status-dot"></span>
                <span class="sidebar-status-text">API 已连接</span><br>
                <span class="sidebar-status-sub">{st.session_state.backend.upper()} / {st.session_state.model}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # 功能模块导航
        st.markdown('<div class="sidebar-section-title">📊 功能模块</div>', unsafe_allow_html=True)

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

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # 使用统计
        st.markdown('<div class="sidebar-section-title">📈 使用统计</div>', unsafe_allow_html=True)
        history_count = len(st.session_state.analysis_history)
        st.markdown(
            f'<div class="sidebar-stats">'
            f'本次会话分析次数: <span class="sidebar-stats-count">{history_count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if history_count > 0 and st.button("🗑️ 清空历史", use_container_width=True):
            st.session_state.analysis_history = []
            st.rerun()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="sidebar-footer">
            <div>Powered by AI</div>
            <div>© 2024 Financial Insight</div>
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
    elif analysis_type == "stock_comparison":
        try:
            render_stock_comparison_result(result)
        except Exception as e:
            st.error(f"❌ 渲染分析结果时出错: {str(e)}")
            with st.expander("查看原始返回数据"):
                st.json(result)


# ============================================================
# 报告导出辅助函数
# ============================================================
def _render_export_buttons(result: Dict[str, Any], analysis_type: str):
    """渲染 PDF/Word 导出按钮"""
    if "error" in result:
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📄 导出为 Word", key=f"export_word_{analysis_type}_{id(result)}", use_container_width=True):
            with st.spinner("正在生成 Word 文档..."):
                try:
                    word_bytes = ReportExporter.export_to_word(result, analysis_type)
                    st.download_button(
                        label="📥 下载 Word 文档",
                        data=word_bytes,
                        file_name=f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"download_word_{analysis_type}_{id(result)}",
                    )
                except Exception as e:
                    st.error(f"❌ Word 导出失败: {str(e)}")
    with col2:
        if st.button("📕 导出为 PDF", key=f"export_pdf_{analysis_type}_{id(result)}", use_container_width=True):
            with st.spinner("正在生成 PDF 文档..."):
                try:
                    pdf_bytes = ReportExporter.export_to_pdf(result, analysis_type)
                    st.download_button(
                        label="📥 下载 PDF 文档",
                        data=pdf_bytes,
                        file_name=f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key=f"download_pdf_{analysis_type}_{id(result)}",
                    )
                except Exception as e:
                    st.error(f"❌ PDF 导出失败: {str(e)}")


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

    # 导出按钮
    _render_export_buttons(result, "news_analysis")


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

    # 导出按钮
    _render_export_buttons(result, "announcement_analysis")


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

    # 导出按钮
    _render_export_buttons(result, "hotspot_analysis")


# ============================================================
# 股票深度解码结果渲染（机构级 Bloomberg 终端风格）
# ============================================================
def _render_scorecard(sc: Dict[str, Any]):
    """渲染综合评分卡（Scorecard）- 企业级增强版"""
    if not sc:
        return
    overall_rating = sc.get("overall_rating", "Hold")
    overall_score = sc.get("overall_score", 50)

    rating_map = {
        "Strong Buy": ("pro-rating-strong-buy", "🔹 强力买入"),
        "Buy": ("pro-rating-buy", "🔸 买入"),
        "Hold": ("pro-rating-hold", "⬜ 持有"),
        "Avoid": ("pro-rating-avoid", "🔻 回避"),
        "Strong Sell": ("pro-rating-strong-sell", "🔻 强力卖出"),
    }
    css_class, label = rating_map.get(overall_rating, ("pro-rating-hold", "⬜ 持有"))

    st.markdown("## 📊 综合评分卡")
    st.markdown("---")

    # ---- 评级徽章 + 综合评分 ----
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(
            f'<div style="text-align:center;padding:1rem;">'
            f'<div class="pro-rating-badge {css_class}">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        score_pct = min(max(overall_score, 0), 100)
        score_color = "#00D4AA" if score_pct >= 60 else "#FFC107" if score_pct >= 40 else "#FF4D4D"
        st.markdown(
            f'<div style="padding:0.5rem 0;">'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="color:#8892B0;font-size:0.85rem;">综合评分</span>'
            f'<span style="color:{score_color};font-size:1.2rem;font-weight:700;">{score_pct}/100</span>'
            f'</div>'
            f'<div style="height:8px;background:rgba(42,45,62,0.5);border-radius:4px;margin-top:4px;">'
            f'<div style="height:100%;width:{score_pct}%;background:{score_color};border-radius:4px;transition:width 0.5s;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ---- 评级刻度表（专业机构级分段定义） ----
    rating_scale = sc.get("rating_scale", [])
    if rating_scale and isinstance(rating_scale, list):
        with st.expander("📊 评级刻度表 — 评分分段标准定义", expanded=False):
            scale_rows = ""
            for item in rating_scale:
                r = item.get("range", "")
                rating = item.get("rating", "")
                meaning = item.get("meaning", "")
                action = item.get("action", "")
                color = item.get("color", "#8892B0")
                is_active = False
                if r:
                    parts = r.split("-")
                    if len(parts) == 2:
                        try:
                            low, high = int(parts[0]), int(parts[1])
                            is_active = low <= overall_score <= high
                        except ValueError:
                            pass
                active_class = "active-row" if is_active else ""
                scale_rows += (
                    f'<tr class="{active_class}">'
                    f'<td><span class="scale-indicator" style="background:{color};"></span>'
                    f'<span class="scale-range">{r}</span></td>'
                    f'<td><span class="scale-rating" style="color:{color};">{rating}</span></td>'
                    f'<td><div class="scale-meaning">{meaning}</div></td>'
                    f'<td><span class="scale-action" style="color:{color};">{action}</span></td>'
                    f'</tr>'
                )
            st.markdown(
                f'<table class="pro-rating-scale">'
                f'<thead><tr>'
                f'<th style="width:10%;">分数段</th>'
                f'<th style="width:18%;">评级</th>'
                f'<th style="width:52%;">含义解读</th>'
                f'<th style="width:20%;">建议操作</th>'
                f'</tr></thead>'
                f'<tbody>{scale_rows}</tbody>'
                f'</table>',
                unsafe_allow_html=True,
            )

    # ---- 评分方法论摘要（可展开） ----
    scoring_summary = sc.get("scoring_summary", "")
    scoring_data_sources = sc.get("scoring_data_sources", "")
    scoring_criteria = sc.get("scoring_criteria", "")
    if scoring_summary or scoring_data_sources or scoring_criteria:
        with st.expander("📋 评分方法论 · 数据来源 · 评分标准", expanded=False):
            if scoring_summary:
                st.markdown(
                    f'<div class="pro-scoring-summary-box">'
                    f'<div class="pro-scoring-summary-label">📐 评分方法论</div>'
                    f'<div class="pro-scoring-summary-text">{scoring_summary}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if scoring_data_sources:
                st.markdown(
                    f'<div class="pro-data-source-box">'
                    f'<div class="pro-data-source-label">📡 数据来源</div>'
                    f'<div class="pro-data-source-text">{scoring_data_sources}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if scoring_criteria:
                st.markdown(
                    f'<div class="pro-scoring-criteria-box">'
                    f'<div class="pro-scoring-criteria-label">⚖️ 评分标准总则</div>'
                    f'<div class="pro-scoring-criteria-text">{scoring_criteria}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ---- 六维评分（含评分依据/数据来源/评分标准详情） ----
    dimensions = sc.get("dimensions", {})
    if dimensions and isinstance(dimensions, dict):
        st.markdown("### 📐 六维评分")
        dim_config = [
            ("market_identity", "市场身份", "#00A3FF", "🏛️"),
            ("technical", "技术面", "#00D4AA", "📈"),
            ("fundamental", "基本面", "#9C27B0", "📊"),
            ("sentiment", "情绪面", "#FFC107", "🔥"),
            ("risk_reward", "风险收益", "#FF9800", "⚖️"),
            ("liquidity", "流动性", "#E040FB", "💧"),
        ]
        for key, dim_label, dim_color, dim_icon in dim_config:
            dim_score = dimensions.get(key, {})
            if isinstance(dim_score, dict):
                score_val = dim_score.get("score", 50)
                comment = dim_score.get("comment", "")
                scoring_basis = dim_score.get("scoring_basis", "")
                data_sources = dim_score.get("data_sources", "")
                scoring_criteria = dim_score.get("scoring_criteria", "")
            else:
                score_val = dim_score if isinstance(dim_score, (int, float)) else 50
                comment = ""
                scoring_basis = ""
                data_sources = ""
                scoring_criteria = ""
            score_val = min(max(score_val, 0), 100)
            bar_color = "#00D4AA" if score_val >= 60 else "#FFC107" if score_val >= 40 else "#FF4D4D"

            # 评分条 + 评分按钮
            st.markdown(
                f'<div style="margin:0.5rem 0;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span class="pro-dimension-label" style="color:{dim_color};font-size:0.8rem;">{dim_icon} {dim_label}</span>'
                f'<span class="pro-dimension-score" style="color:{bar_color};">{score_val}</span>'
                f'</div>'
                f'<div class="pro-dimension-bar" style="background:rgba(42,45,62,0.5);">'
                f'<div class="pro-dimension-bar" style="width:{score_val}%;background:{bar_color};"></div>'
                f'</div>'
                f'<div style="color:#6A6D7E;font-size:0.7rem;margin-top:2px;">{comment}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 评分详情（可展开）- 使用 st.expander 实现
            has_details = any([scoring_basis, data_sources, scoring_criteria])
            if has_details:
                detail_key = f"scoring_detail_{key}"
                with st.expander(f"📖 查看 {dim_label} 评分详情", expanded=False):
                    if scoring_basis:
                        st.markdown(
                            f'<div class="pro-scoring-detail">'
                            f'<div class="pro-scoring-detail-label">📌 评分依据</div>'
                            f'<div class="pro-scoring-detail-text">{scoring_basis}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    if data_sources:
                        st.markdown(
                            f'<div class="pro-data-source-box">'
                            f'<div class="pro-data-source-label">📡 数据来源</div>'
                            f'<div class="pro-data-source-text">{data_sources}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    if scoring_criteria:
                        st.markdown(
                            f'<div class="pro-scoring-criteria-box">'
                            f'<div class="pro-scoring-criteria-label">⚖️ 评分标准</div>'
                            f'<div class="pro-scoring-criteria-text">{scoring_criteria}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # ---- 关键风险 ----
    risks = sc.get("key_risks", [])
    if risks and isinstance(risks, list):
        st.markdown("### ⚠️ 关键风险")
        risk_html = ""
        for r in risks:
            risk_level = "high" if any(w in str(r).lower() for w in ["高", "严重", "重大", "风险"]) else "mid"
            risk_html += f'<span class="pro-risk-tag pro-risk-{risk_level}">{r}</span> '
        st.markdown(f'<div>{risk_html}</div>', unsafe_allow_html=True)

    # ---- 关键催化剂 ----
    catalysts = sc.get("key_catalysts", [])
    if catalysts and isinstance(catalysts, list):
        st.markdown("### 🚀 关键催化剂")
        for c in catalysts:
            st.markdown(
                f'<div style="color:#00D4AA;font-size:0.85rem;margin:0.2rem 0;">▸ {c}</div>',
                unsafe_allow_html=True,
            )


def _pro_data_row(label: str, value: str, signal: str = ""):
    """渲染专业数据行"""
    signal_class = ""
    if signal == "up":
        signal_class = "pro-data-value-up"
    elif signal == "down":
        signal_class = "pro-data-value-down"
    elif signal == "bullish":
        signal_class = "pro-signal-bullish"
    elif signal == "bearish":
        signal_class = "pro-signal-bearish"
    elif signal == "neutral":
        signal_class = "pro-signal-neutral"
    return f'<div class="pro-data-row"><span class="pro-data-label">{label}</span><span class="pro-data-value {signal_class}">{value}</span></div>'


def _pro_section(label: str, value: str, color: str = "#00D4AA"):
    """渲染专业分析段落"""
    header_class = "pro-section-header-info"
    if color == "#00D4AA":
        header_class = "pro-section-header-buy"
    elif color == "#FF4D4D":
        header_class = "pro-section-header-sell"
    elif color == "#FFC107":
        header_class = "pro-section-header-neutral"
    return f'<div class="pro-section-header {header_class}">{label}</div><div style="padding:0.5rem 1rem;color:#E8E8E8;line-height:1.6;font-size:0.9rem;">{value}</div>'


def render_stock_decode_result(result: Dict[str, Any]):
    """渲染股票深度解码分析结果（机构级 Bloomberg 终端风格）"""
    required_parts = ["part1_market_identity", "part2_price_action", "part3_technical_analysis", "part4_drivers_sentiment", "part5_outlook_strategy"]
    missing_parts = [p for p in required_parts if p not in result]
    if missing_parts:
        st.warning(f"⚠️ 分析结果部分缺失: {', '.join(missing_parts)}，显示已有内容")

    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    # ===== 综合评分卡 =====
    scorecard = result.get("scorecard", {})
    if scorecard:
        _render_scorecard(scorecard)

    # ===== 第一部分：股票身份与跨境监管透视 =====
    part1 = result.get("part1_market_identity", {})
    if part1 and isinstance(part1, dict):
        st.markdown("## 🔍 第一部分：股票身份与跨境监管透视")
        st.markdown("---")

        market = part1.get("market_judgment", {})
        if market:
            st.markdown(_pro_section("基本信息", ""), unsafe_allow_html=True)
            rows = ""
            rows += _pro_data_row("所属市场", market.get("market", "未知"))
            rows += _pro_data_row("交易所", market.get("exchange", "未知"))
            rows += _pro_data_row("监管机构", market.get("regulator", "未知"))
            rows += _pro_data_row("上市公司", market.get("stock_name", "未知"))
            rows += _pro_data_row("业务板块", market.get("business_sector", ""))
            rows += _pro_data_row("市值层级", market.get("market_cap_tier", ""))
            rows += _pro_data_row("指数成分", market.get("index_membership", ""))
            st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)
            reason = market.get("reason", "")
            if reason:
                st.markdown(f'<div style="color:#6A6D7E;font-size:0.8rem;padding:0 1rem 0.5rem 1rem;">📌 {reason}</div>', unsafe_allow_html=True)

        rules = part1.get("trading_rules", {})
        if rules:
            st.markdown(_pro_section("监管合规与交易机制", "", "#00A3FF"), unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f'<div class="pro-level-card pro-level-support">'
                    f'<div style="color:#8892B0;font-size:0.7rem;">结算方式</div>'
                    f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{rules.get("settlement", "未知")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="pro-level-card pro-level-resistance">'
                    f'<div style="color:#8892B0;font-size:0.7rem;">涨跌幅限制</div>'
                    f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{rules.get("price_limit", "未知")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<div class="pro-level-card pro-level-stop">'
                    f'<div style="color:#8892B0;font-size:0.7rem;">融券做空</div>'
                    f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{rules.get("short_selling", "未知")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        thresholds = part1.get("abnormal_thresholds", {})
        if thresholds:
            st.markdown(_pro_section("异动公告触发临界点", "", "#FF4D4D"), unsafe_allow_html=True)

            # 异动触发状态指示器
            triggered = thresholds.get("triggered", False)
            triggered_details = thresholds.get("triggered_details", "")
            if triggered:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.6rem 1rem;background:rgba(255,77,77,0.12);'
                    f'border-left:4px solid #FF4D4D;border-radius:0 8px 8px 0;">'
                    f'<div style="color:#FF4D4D;font-size:0.9rem;font-weight:700;">🚨 该股票已触发异动条件</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{triggered_details}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.6rem 1rem;background:rgba(0,212,170,0.08);'
                    f'border-left:4px solid #00D4AA;border-radius:0 8px 8px 0;">'
                    f'<div style="color:#00D4AA;font-size:0.9rem;font-weight:700;">✅ 当前处于正常波动范围</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{triggered_details if triggered_details else "该股票近期价格和成交量未触发异动公告条件，市场交易行为正常。"}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            rule_desc = thresholds.get("rule_description", "")
            if rule_desc:
                st.markdown(f'<div style="color:#8892B0;font-size:0.8rem;padding:0.3rem 1rem;">📌 {rule_desc}</div>', unsafe_allow_html=True)

            # 动态展示各市场规则（只显示与当前股票相关的）
            market_rules = {
                "a_share_mainboard": ("A股主板规则", thresholds.get("a_share_mainboard", "")),
                "a_share_chi_next": ("创业板/科创板规则", thresholds.get("a_share_chi_next", "")),
                "a_share_beijing": ("北交所规则", thresholds.get("a_share_beijing", "")),
                "hk_stock": ("港股规则", thresholds.get("hk_stock", "")),
                "us_stock": ("美股规则", thresholds.get("us_stock", "")),
                "special_treatment": ("ST/*ST风险警示板规则", thresholds.get("special_treatment", "")),
            }
            for key, (label, val) in market_rules.items():
                if val:
                    st.markdown(
                        f'<div style="margin:0.2rem 1rem;padding:0.3rem 0.8rem;background:rgba(255,255,255,0.03);'
                        f'border-radius:6px;color:#C0C0C0;font-size:0.8rem;">📋 {label}：{val}</div>',
                        unsafe_allow_html=True,
                    )

            volume_alert = thresholds.get("volume_alert", "")
            if volume_alert:
                st.markdown(
                    f'<div style="margin:0.2rem 1rem;padding:0.3rem 0.8rem;background:rgba(255,255,255,0.03);'
                    f'border-radius:6px;color:#C0C0C0;font-size:0.8rem;">📊 {volume_alert}</div>',
                    unsafe_allow_html=True,
                )

        circ = part1.get("circulation_info", {})
        if circ:
            st.markdown(_pro_section("股本结构与融资融券", "", "#00A3FF"), unsafe_allow_html=True)
            rows = ""
            rows += _pro_data_row("流通股本", circ.get("circulating_shares", ""))
            rows += _pro_data_row("总股本", circ.get("total_shares", ""))
            rows += _pro_data_row("融资融券", circ.get("margin_trading", ""))
            rows += _pro_data_row("流通市值", circ.get("circulating_market_cap", ""))
            st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)

    # ===== 第二部分：盘面异动与资金行为推演 =====
    part2 = result.get("part2_price_action", {})
    if part2:
        st.markdown("## 📊 第二部分：盘面异动与资金行为推演")
        st.markdown("---")

        st.markdown(_pro_section("异动状态评估", part2.get("abnormal_assessment", ""), "#FF4D4D"), unsafe_allow_html=True)
        st.markdown(_pro_section("资金行为推演", part2.get("capital_flow_analysis", ""), "#00A3FF"), unsafe_allow_html=True)
        st.markdown(_pro_section("盘中急涨急跌异动", part2.get("intraday_anomaly", ""), "#FF9800"), unsafe_allow_html=True)

        vp = part2.get("volume_price_analysis", "")
        if vp:
            st.markdown(_pro_section("量价关系深度分析", vp, "#E040FB"), unsafe_allow_html=True)

        order_flow = part2.get("order_flow_insight", "")
        if order_flow:
            st.markdown(_pro_section("订单流洞察", order_flow, "#00A3FF"), unsafe_allow_html=True)

        inst = part2.get("institutional_behavior", "")
        if inst:
            st.markdown(_pro_section("机构行为分析", inst, "#9C27B0"), unsafe_allow_html=True)

    # ===== 第三部分：技术面深度分析 =====
    part3_tech = result.get("part3_technical_analysis", {})
    if part3_tech and isinstance(part3_tech, dict):
        st.markdown("## 📐 第三部分：技术面深度分析")
        st.markdown("---")

        trend = part3_tech.get("trend_analysis", {})
        if trend and isinstance(trend, dict):
            st.markdown(_pro_section("趋势研判", "", "#00A3FF"), unsafe_allow_html=True)
            rows = ""
            rows += _pro_data_row("短期趋势（5/10/20日）", trend.get("short_term_trend", ""), "up" if "涨" in str(trend.get("short_term_trend", "")) else "down")
            rows += _pro_data_row("中期趋势（60日）", trend.get("mid_term_trend", ""), "up" if "涨" in str(trend.get("mid_term_trend", "")) else "down")
            rows += _pro_data_row("长期趋势（120/250日）", trend.get("long_term_trend", ""))
            rows += _pro_data_row("通道状态", trend.get("channel_status", ""))
            st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)
            key_levels = trend.get("key_levels", "")
            if key_levels:
                st.markdown(f'<div style="color:#E8E8E8;font-size:0.85rem;padding:0.3rem 1rem;">🎯 关键价位: {key_levels}</div>', unsafe_allow_html=True)

        momentum = part3_tech.get("momentum_indicators", {})
        if momentum and isinstance(momentum, dict):
            st.markdown(_pro_section("动量指标", "", "#FFC107"), unsafe_allow_html=True)
            cols = st.columns(4)
            indicators = [
                ("MACD", momentum.get("macd", ""), "#00D4AA"),
                ("KDJ", momentum.get("kdj", ""), "#00A3FF"),
                ("RSI", momentum.get("rsi", ""), "#FFC107"),
                ("CCI", momentum.get("cci", ""), "#E040FB"),
            ]
            for i, (label, val, color) in enumerate(indicators):
                with cols[i]:
                    st.markdown(
                        f'<div class="pro-indicator-card" style="border-top:2px solid {color};">'
                        f'<div class="pro-indicator-value" style="color:{color};">{val}</div>'
                        f'<div class="pro-indicator-label">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        vol_insight = part3_tech.get("volume_insight", "")
        if vol_insight:
            st.markdown(_pro_section("成交量能分析", vol_insight, "#E040FB"), unsafe_allow_html=True)

        boll = part3_tech.get("bollinger_analysis", "")
        if boll:
            st.markdown(_pro_section("布林带分析", boll, "#00A3FF"), unsafe_allow_html=True)

        wave = part3_tech.get("wave_theory", "")
        if wave:
            st.markdown(_pro_section("波浪理论分析", wave, "#9C27B0"), unsafe_allow_html=True)

        div_alert = part3_tech.get("divergence_alert", "")
        if div_alert:
            st.markdown(_pro_section("背离信号预警", div_alert, "#FF4D4D"), unsafe_allow_html=True)

    # ===== 第四部分：核心驱动力与舆情情绪拆解 =====
    part4 = result.get("part4_drivers_sentiment", {})
    if part4:
        st.markdown("## 💣 第四部分：核心驱动力与舆情情绪拆解")
        st.markdown("---")

        # ---- 板块分析（小白友好） ----
        sector = part4.get("sector_analysis", {})
        if sector:
            st.markdown(_pro_section("📌 行业板块深度分析", "", "#00D4AA"), unsafe_allow_html=True)

            belonging = sector.get("belonging_sector", "")
            if belonging:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,0,0,0.15);border-radius:6px;">'
                    f'<div style="color:#00D4AA;font-size:0.8rem;font-weight:600;">🏢 所属行业板块</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{belonging}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            position = sector.get("sector_position", "")
            if position:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,0,0,0.15);border-radius:6px;">'
                    f'<div style="color:#FFC107;font-size:0.8rem;font-weight:600;">👑 板块地位</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{position}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            perf = sector.get("sector_performance", "")
            if perf:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,0,0,0.15);border-radius:6px;">'
                    f'<div style="color:#00A3FF;font-size:0.8rem;font-weight:600;">📈 板块近期表现</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{perf}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            peer = sector.get("peer_comparison", "")
            if peer:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,0,0,0.15);border-radius:6px;">'
                    f'<div style="color:#E040FB;font-size:0.8rem;font-weight:600;">🔍 同行对比</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{peer}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            catalyst = sector.get("sector_catalyst", "")
            if catalyst:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,212,170,0.08);'
                    f'border-left:3px solid #00D4AA;border-radius:0 6px 6px 0;">'
                    f'<div style="color:#00D4AA;font-size:0.8rem;font-weight:600;">⚡ 板块催化剂</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{catalyst}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            risk = sector.get("sector_risk", "")
            if risk:
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(255,77,77,0.08);'
                    f'border-left:3px solid #FF4D4D;border-radius:0 6px 6px 0;">'
                    f'<div style="color:#FF4D4D;font-size:0.8rem;font-weight:600;">⚠️ 板块风险提示</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;margin-top:0.2rem;">{risk}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        drivers = part4.get("driver_types", {})
        if drivers:
            st.markdown(_pro_section("驱动力分类", "", "#00A3FF"), unsafe_allow_html=True)
            for d_key, d_val in drivers.items():
                icons = {"fundamental": "📊", "policy": "🏛️", "sentiment": "🔥", "valuation": "💰"}
                labels = {"fundamental": "基本面驱动", "policy": "政策周期驱动", "sentiment": "情绪题材驱动", "valuation": "估值驱动"}
                st.markdown(
                    f'<div style="margin:0.3rem 1rem;padding:0.5rem;background:rgba(0,0,0,0.15);border-radius:6px;">'
                    f'<div style="color:#00D4AA;font-size:0.8rem;font-weight:600;">{icons.get(d_key, "📌")} {labels.get(d_key, d_key)}</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.2rem;">{d_val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        sentiment = part4.get("market_sentiment", {})
        if sentiment:
            st.markdown(_pro_section("市场情绪量化模拟", "", "#FFC107"), unsafe_allow_html=True)
            rows = ""
            rows += _pro_data_row("整体情绪", sentiment.get("overall", ""), "bullish" if "乐观" in str(sentiment.get("overall", "")) or "看多" in str(sentiment.get("overall", "")) else "bearish")
            rows += _pro_data_row("看跌/看涨比", sentiment.get("put_call_ratio", ""))
            rows += _pro_data_row("媒体情绪", sentiment.get("media_sentiment", ""))
            rows += _pro_data_row("聪明钱追踪", sentiment.get("smart_money_track", ""))
            st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)

            risk = sentiment.get("risk_warning", "")
            if risk:
                st.markdown(
                    f'<div style="margin:0.5rem 1rem;padding:0.5rem 1rem;background:rgba(255,77,77,0.08);'
                    f'border-left:3px solid #FF4D4D;border-radius:0 6px 6px 0;">'
                    f'<div style="color:#FF4D4D;font-size:0.8rem;font-weight:600;">⚠️ 风险警告</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{risk}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            crowd = sentiment.get("crowd_behavior", "")
            if crowd:
                st.markdown(_pro_section("散户/机构情绪分化", crowd, "#E040FB"), unsafe_allow_html=True)

    # ===== 第五部分：空间博弈与多空展望 =====
    part5 = result.get("part5_outlook_strategy", {})
    if part5:
        st.markdown("## 🚀 第五部分：空间博弈与多空展望")
        st.markdown("---")

        tech = part5.get("technical_levels", {})
        if tech:
            st.markdown(_pro_section("关键价位矩阵", "", "#FFC107"), unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                s1 = tech.get("support_1", tech.get("support", ""))
                st.markdown(
                    f'<div class="pro-level-card pro-level-support">'
                    f'<div style="color:#00D4AA;font-size:0.7rem;font-weight:600;">🛡️ 一级支撑</div>'
                    f'<div style="color:#E8E8E8;font-size:1.2rem;font-weight:700;">{s1}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                s2 = tech.get("support_2", "")
                st.markdown(
                    f'<div class="pro-level-card pro-level-support" style="border-top-color:#00D4AA;opacity:0.8;">'
                    f'<div style="color:#00D4AA;font-size:0.7rem;font-weight:600;">🛡️ 二级支撑</div>'
                    f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{s2}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                s3 = tech.get("support_3", "")
                st.markdown(
                    f'<div class="pro-level-card pro-level-support" style="border-top-color:#00D4AA;opacity:0.6;">'
                    f'<div style="color:#00D4AA;font-size:0.7rem;font-weight:600;">🛡️ 三级支撑</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;">{s3}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            col1, col2, col3 = st.columns(3)
            with col1:
                r1 = tech.get("resistance_1", tech.get("resistance", ""))
                st.markdown(
                    f'<div class="pro-level-card pro-level-resistance">'
                    f'<div style="color:#FF4D4D;font-size:0.7rem;font-weight:600;">🚧 一级阻力</div>'
                    f'<div style="color:#E8E8E8;font-size:1.2rem;font-weight:700;">{r1}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                r2 = tech.get("resistance_2", "")
                st.markdown(
                    f'<div class="pro-level-card pro-level-resistance" style="border-top-color:#FF4D4D;opacity:0.8;">'
                    f'<div style="color:#FF4D4D;font-size:0.7rem;font-weight:600;">🚧 二级阻力</div>'
                    f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{r2}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                r3 = tech.get("resistance_3", "")
                st.markdown(
                    f'<div class="pro-level-card pro-level-resistance" style="border-top-color:#FF4D4D;opacity:0.6;">'
                    f'<div style="color:#FF4D4D;font-size:0.7rem;font-weight:600;">🚧 三级阻力</div>'
                    f'<div style="color:#E8E8E8;font-size:0.9rem;">{r3}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            stop_loss = tech.get("stop_loss", "")
            take_profit = tech.get("take_profit", "")
            if stop_loss or take_profit:
                col1, col2 = st.columns(2)
                with col1:
                    if stop_loss:
                        st.markdown(
                            f'<div class="pro-level-card pro-level-stop">'
                            f'<div style="color:#FF9800;font-size:0.7rem;font-weight:600;">🛑 止损参考位</div>'
                            f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{stop_loss}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                with col2:
                    if take_profit:
                        st.markdown(
                            f'<div class="pro-level-card pro-level-support">'
                            f'<div style="color:#00D4AA;font-size:0.7rem;font-weight:600;">🎯 止盈参考位</div>'
                            f'<div style="color:#E8E8E8;font-size:1rem;font-weight:600;">{take_profit}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

        rr = part5.get("risk_reward_ratio", {})
        if rr:
            st.markdown(_pro_section("风险收益比评估", "", "#FF9800"), unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f'<div class="pro-indicator-card">'
                    f'<div class="pro-indicator-value" style="color:#00D4AA;">{rr.get("upside_space", "—")}</div>'
                    f'<div class="pro-indicator-label">📈 上行空间</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div class="pro-indicator-card">'
                    f'<div class="pro-indicator-value" style="color:#FF4D4D;">{rr.get("downside_space", "—")}</div>'
                    f'<div class="pro-indicator-label">📉 下行风险</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<div class="pro-indicator-card">'
                    f'<div class="pro-indicator-value" style="color:#FFC107;">{rr.get("ratio", "—")}</div>'
                    f'<div class="pro-indicator-label">⚖️ 风险收益比</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            var_est = rr.get("var_estimate", "")
            if var_est:
                st.markdown(f'<div style="color:#6A6D7E;font-size:0.8rem;padding:0.3rem 0;">VaR 估算: {var_est}</div>', unsafe_allow_html=True)
            max_dd = rr.get("max_drawdown_alert", "")
            if max_dd:
                st.markdown(f'<div style="color:#FF4D4D;font-size:0.8rem;padding:0.3rem 0;">⚠️ 最大回撤预警: {max_dd}</div>', unsafe_allow_html=True)

        strategy = part5.get("strategy_advice", {})
        if strategy:
            st.markdown(_pro_section("操盘策略建议", "", "#00D4AA"), unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.8rem;margin:0.3rem 0;border-left:3px solid #00D4AA;">'
                    f'<div style="color:#00D4AA;font-size:0.8rem;font-weight:600;">⚡ 短线趋势交易者</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{strategy.get("short_term", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.8rem;margin:0.3rem 0;border-left:3px solid #00A3FF;">'
                    f'<div style="color:#00A3FF;font-size:0.8rem;font-weight:600;">💎 中线价值投资者</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{strategy.get("mid_term", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            risk_mgmt = strategy.get("risk_management", "")
            if risk_mgmt:
                st.markdown(
                    f'<div style="margin:0.5rem 0;padding:0.5rem 1rem;background:rgba(255,77,77,0.08);'
                    f'border-left:4px solid #FF4D4D;border-radius:0 6px 6px 0;">'
                    f'<div style="color:#FF4D4D;font-size:0.8rem;font-weight:600;">⚠️ 风险管理建议</div>'
                    f'<div style="color:#E8E8E8;font-size:0.85rem;margin-top:0.3rem;">{risk_mgmt}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            pos = strategy.get("position_sizing", {})
            if pos and isinstance(pos, dict):
                st.markdown(_pro_section("仓位管理方案", "", "#FFC107"), unsafe_allow_html=True)
                rows = ""
                rows += _pro_data_row("建议仓位", pos.get("suggested_position", ""))
                rows += _pro_data_row("入场策略", pos.get("entry_strategy", ""))
                rows += _pro_data_row("金字塔加仓", pos.get("pyramid_position", ""))
                rows += _pro_data_row("减仓策略", pos.get("reduction_strategy", ""))
                st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)

            horizon = strategy.get("time_horizon", {})
            if horizon and isinstance(horizon, dict):
                st.markdown(_pro_section("时间维度展望", "", "#00A3FF"), unsafe_allow_html=True)
                rows = ""
                rows += _pro_data_row("短期展望（1-5日）", horizon.get("short_term", ""))
                rows += _pro_data_row("中期展望（1-3月）", horizon.get("mid_term", ""))
                rows += _pro_data_row("长期展望（6-12月）", horizon.get("long_term", ""))
                st.markdown(f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;margin:0.5rem 0;">{rows}</div>', unsafe_allow_html=True)

        scenario = part5.get("scenario_analysis", {})
        if scenario and isinstance(scenario, dict):
            st.markdown(_pro_section("情景分析", "", "#FFC107"), unsafe_allow_html=True)
            sc_col1, sc_col2, sc_col3 = st.columns(3)
            with sc_col1:
                bull = scenario.get("bull_case", {})
                if isinstance(bull, str):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-bull">'
                        f'<div style="color:#00D4AA;font-size:0.85rem;font-weight:600;">📈 乐观情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.5rem;">{bull}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                elif isinstance(bull, dict):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-bull">'
                        f'<div style="color:#00D4AA;font-size:0.85rem;font-weight:600;">📈 乐观情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.3rem;">{bull.get("trigger", "")}</div>'
                        f'<div style="color:#00D4AA;font-size:1rem;font-weight:700;margin-top:0.3rem;">{bull.get("target_price", "")}</div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:0.3rem;">'
                        f'<span style="color:#00D4AA;font-size:0.8rem;">概率 {bull.get("probability", "")}</span>'
                        f'<span style="color:#E8E8E8;font-size:0.8rem;">预期收益 {bull.get("expected_return", "")}</span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
            with sc_col2:
                bear = scenario.get("bear_case", {})
                if isinstance(bear, str):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-bear">'
                        f'<div style="color:#FF4D4D;font-size:0.85rem;font-weight:600;">📉 悲观情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.5rem;">{bear}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                elif isinstance(bear, dict):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-bear">'
                        f'<div style="color:#FF4D4D;font-size:0.85rem;font-weight:600;">📉 悲观情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.3rem;">{bear.get("trigger", "")}</div>'
                        f'<div style="color:#FF4D4D;font-size:1rem;font-weight:700;margin-top:0.3rem;">{bear.get("target_price", "")}</div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:0.3rem;">'
                        f'<span style="color:#FF4D4D;font-size:0.8rem;">概率 {bear.get("probability", "")}</span>'
                        f'<span style="color:#E8E8E8;font-size:0.8rem;">预期收益 {bear.get("expected_return", "")}</span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
            with sc_col3:
                base = scenario.get("base_case", {})
                if isinstance(base, str):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-base">'
                        f'<div style="color:#FFC107;font-size:0.85rem;font-weight:600;">⚖️ 基准情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.5rem;">{base}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                elif isinstance(base, dict):
                    st.markdown(
                        f'<div class="pro-scenario-card pro-scenario-base">'
                        f'<div style="color:#FFC107;font-size:0.85rem;font-weight:600;">⚖️ 基准情景</div>'
                        f'<div style="color:#E8E8E8;font-size:0.8rem;margin-top:0.3rem;">{base.get("trigger", "")}</div>'
                        f'<div style="color:#FFC107;font-size:1rem;font-weight:700;margin-top:0.3rem;">{base.get("target_price", "")}</div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:0.3rem;">'
                        f'<span style="color:#FFC107;font-size:0.8rem;">概率 {base.get("probability", "")}</span>'
                        f'<span style="color:#E8E8E8;font-size:0.8rem;">预期收益 {base.get("expected_return", "")}</span>'
                        f'</div></div>',
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

    # 导出按钮
    _render_export_buttons(result, "stock_deep_decode")


# ============================================================
# 功能页面
# ============================================================
def render_news_analysis_page():
    """财经新闻分析页面"""
    st.markdown('<div class="page-header">📰 财经新闻分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">输入财经新闻，AI 自动分析总结、利好利空判断、风险提示</div>',
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
    st.markdown('<div class="page-header">📋 上市公司公告分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">输入公告内容，AI 提取核心事件、财务数据和风险提示</div>',
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
    st.markdown('<div class="page-header">🔥 市场热点分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">输入多条财经新闻，AI 提取市场热点、热门行业和公司</div>',
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


# ============================================================
# 股票深度解码 - 辅助渲染函数
# ============================================================


def _render_radar_chart(scores: Dict[str, float]) -> go.Figure:
    """绘制六维评分雷达图"""
    dimensions = [
        "市场身份", "技术面", "基本面", "情绪面", "风险收益", "流动性"
    ]
    dim_keys = ["market_identity", "technical", "fundamental",
                "sentiment", "risk_reward", "liquidity"]

    values = [scores.get(k, 0) for k in dim_keys]
    values_closed = values + [values[0]]
    dims_closed = dimensions + [dimensions[0]]

    fig = go.Figure()
    # 60分参考线
    fig.add_trace(go.Scatterpolar(
        r=[60] * len(dims_closed),
        theta=dims_closed,
        name="及格线 (60)",
        line=dict(color="rgba(255, 255, 255, 0.15)", width=1, dash="dash"),
        showlegend=True,
    ))
    # 评分区域
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=dims_closed,
        fill="toself",
        name="评分",
        line=dict(color="#00D4AA", width=2),
        fillcolor="rgba(0, 212, 170, 0.2)",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="#8892B0", size=10),
                gridcolor="rgba(255,255,255,0.08)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#CCD6F6", size=12),
                gridcolor="rgba(255,255,255,0.08)",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CCD6F6"),
        margin=dict(l=80, r=80, t=30, b=30),
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#8892B0", size=11),
        ),
    )
    return fig


def _render_gauge_chart(score: float) -> go.Figure:
    """绘制仪表盘评分图"""
    # 颜色分段
    if score >= 90:
        color = "#00D4AA"
    elif score >= 75:
        color = "#00E676"
    elif score >= 60:
        color = "#76FF03"
    elif score >= 45:
        color = "#FFC107"
    elif score >= 30:
        color = "#FF9800"
    elif score >= 15:
        color = "#FF4D4D"
    else:
        color = "#D32F2F"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        number=dict(
            font=dict(size=48, color=color, family="Arial Black"),
            suffix=" 分",
        ),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=1,
                tickcolor="#8892B0",
                tickfont=dict(size=11, color="#8892B0"),
                nticks=11,
            ),
            bar=dict(color=color, thickness=0.3),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[0, 15], color="rgba(211,47,47,0.15)"),
                dict(range=[15, 30], color="rgba(255,77,77,0.12)"),
                dict(range=[30, 45], color="rgba(255,152,0,0.12)"),
                dict(range=[45, 60], color="rgba(255,193,7,0.12)"),
                dict(range=[60, 75], color="rgba(118,255,3,0.10)"),
                dict(range=[75, 90], color="rgba(0,230,118,0.10)"),
                dict(range=[90, 100], color="rgba(0,212,170,0.12)"),
            ],
            threshold=dict(
                line=dict(color="white", width=3),
                thickness=0.6,
                value=score,
            ),
        ),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CCD6F6"),
        margin=dict(l=30, r=30, t=30, b=30),
        height=280,
    )
    return fig


def _render_fund_flow_chart(market_data: Dict[str, Any]) -> Optional[go.Figure]:
    """绘制资金流向柱状图"""
    fund_flow = market_data.get("fund_flow", {})
    if not fund_flow:
        return None

    categories = ["主力净流入", "超大单净流入", "大单净流入", "中单净流入", "小单净流入"]
    keys = ["main_net_inflow", "super_large_net_inflow", "large_net_inflow",
            "medium_net_inflow", "small_net_inflow"]
    values = []
    for k in keys:
        v = fund_flow.get(k, 0)
        try:
            values.append(float(str(v).replace(",", "").replace("亿", "").replace("元", "").strip()))
        except (ValueError, TypeError):
            values.append(0)

    colors = ["#00D4AA" if v >= 0 else "#FF4D4D" for v in values]

    fig = go.Figure(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        marker_line=dict(width=0),
        text=[f"{v:.2f}亿" if abs(v) > 0 else "0" for v in values],
        textposition="outside",
        textfont=dict(color="#CCD6F6", size=12),
    ))
    fig.update_layout(
        title=dict(
            text="实时资金流向 (单位: 亿元)",
            font=dict(color="#CCD6F6", size=14),
            x=0.5,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8892B0"),
        xaxis=dict(
            tickfont=dict(color="#CCD6F6", size=11),
            gridcolor="rgba(255,255,255,0.05)",
        ),
        yaxis=dict(
            tickfont=dict(color="#8892B0", size=10),
            gridcolor="rgba(255,255,255,0.05)",
            zerolinecolor="rgba(255,255,255,0.15)",
        ),
        margin=dict(l=50, r=50, t=50, b=30),
        height=350,
        hovermode="x",
    )
    return fig


def _render_realtime_quote_panel(market_data: Dict[str, Any], stock_input: str):
    """渲染实时报价面板"""
    quote = market_data.get("quote", {})
    tech = market_data.get("technical", {})

    # 主要指标
    st.markdown("### 💹 实时行情")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        price = quote.get("current", quote.get("price", "N/A"))
        change = quote.get("change", quote.get("change_pct", ""))
        change_str = str(change)
        is_up = "+" in change_str or (change_str not in ["N/A", "", "0"] and float(change_str.replace("%", "")) > 0) if change_str.replace("%", "").replace(".", "").replace("-", "").isdigit() else False
        st.metric("最新价", price, change)
    with col2:
        st.metric("开盘", quote.get("open", "N/A"))
    with col3:
        st.metric("最高", quote.get("high", "N/A"))
    with col4:
        st.metric("最低", quote.get("low", "N/A"))
    with col5:
        st.metric("昨收", quote.get("pre_close", quote.get("close", "N/A")))
    with col6:
        st.metric("成交量", quote.get("volume", "N/A"))

    # 扩展指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("成交额", quote.get("amount", tech.get("amount", "N/A")))
    with col2:
        turnover = quote.get("turnover_rate", tech.get("turnover", "N/A"))
        st.metric("换手率", turnover)
    with col3:
        pe = quote.get("pe", tech.get("pe", "N/A"))
        st.metric("市盈率(PE)", pe)
    with col4:
        mcap = quote.get("market_cap", tech.get("market_cap", "N/A"))
        st.metric("总市值", mcap)


def _render_score_dashboard(scorecard: Dict[str, Any], market_data: Dict[str, Any]):
    """渲染综合评分仪表盘 Tab"""
    overall_score = scorecard.get("overall_score", 0)
    rating = scorecard.get("overall_rating", "N/A")
    dimensions = scorecard.get("dimensions", {})
    rating_summary = scorecard.get("rating_summary", "")
    key_risks = scorecard.get("key_risks", [])
    key_catalysts = scorecard.get("key_catalysts", [])
    data_insufficient = scorecard.get("data_insufficient", False)
    data_insufficient_msg = scorecard.get("data_insufficient_message", "")

    # 数据不足警告
    if data_insufficient:
        st.warning(data_insufficient_msg)

    # 顶部：仪表盘 + 评级
    col_gauge, col_rating = st.columns([1, 1])
    with col_gauge:
        gauge_fig = _render_gauge_chart(overall_score)
        st.plotly_chart(gauge_fig, use_container_width=True, config={"displayModeBar": False})

    with col_rating:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1.5rem;height:100%;display:flex;flex-direction:column;justify-content:center;">
            <div style="color:#8892B0;font-size:0.85rem;margin-bottom:0.5rem;">综合评级</div>
            <div style="font-size:1.8rem;font-weight:700;color:#00D4AA;">{rating}</div>
            <div style="color:#6A6D7E;font-size:0.8rem;margin-top:0.5rem;line-height:1.5;">{rating_summary}</div>
        </div>
        """, unsafe_allow_html=True)

    # 评级刻度表
    rating_scale = scorecard.get("rating_scale", [])
    if rating_scale:
        with st.expander("📊 评级刻度表 — 评分分段标准定义", expanded=False):
            scale_html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;">'
            for s in rating_scale:
                color = s.get("color", "#666")
                scale_html += f'''
                <div style="flex:1;min-width:120px;background:rgba(255,255,255,0.03);border-radius:8px;padding:0.8rem;border-left:3px solid {color};">
                    <div style="color:{color};font-size:1.1rem;font-weight:700;">{s["range"]}</div>
                    <div style="color:#CCD6F6;font-size:0.8rem;">{s["rating"]}</div>
                    <div style="color:#6A6D7E;font-size:0.7rem;margin-top:0.3rem;">{s["action"]}</div>
                </div>
                '''
            scale_html += '</div>'
            st.markdown(scale_html, unsafe_allow_html=True)

    # 雷达图 + 各维度评分
    st.markdown("### 🎯 六维评分雷达")
    scores_dict = {k: v.get("score", 0) for k, v in dimensions.items()}
    radar_fig = _render_radar_chart(scores_dict)
    st.plotly_chart(radar_fig, use_container_width=True, config={"displayModeBar": False})

    # 各维度评分详情
    st.markdown("### 📊 各维度评分详情")
    dim_labels = {
        "market_identity": "市场身份", "technical": "技术面",
        "fundamental": "基本面", "sentiment": "情绪面",
        "risk_reward": "风险收益", "liquidity": "流动性",
    }
    for key, label in dim_labels.items():
        dim = dimensions.get(key, {})
        score = dim.get("score", 0)
        comment = dim.get("comment", "")
        basis = dim.get("scoring_basis", "")
        criteria = dim.get("scoring_criteria", "")

        # 颜色
        if score >= 80:
            bar_color = "#00D4AA"
        elif score >= 60:
            bar_color = "#FFC107"
        elif score >= 40:
            bar_color = "#FF9800"
        else:
            bar_color = "#FF4D4D"

        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"**{label}**")
        with col2:
            st.progress(score / 100, text=f"{score:.0f}/100")
            st.markdown(
                f'<div style="color:#6A6D7E;font-size:0.8rem;">{comment}</div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"📖 查看 {label} 评分详情", expanded=False):
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.15);border-radius:8px;padding:1rem;">
                    <div style="color:#8892B0;font-size:0.8rem;margin-bottom:0.3rem;">📌 评分依据</div>
                    <div style="color:#CCD6F6;font-size:0.9rem;margin-bottom:0.8rem;">{basis}</div>
                    <div style="color:#8892B0;font-size:0.8rem;margin-bottom:0.3rem;">📋 评分标准</div>
                    <div style="color:#6A6D7E;font-size:0.85rem;">{criteria}</div>
                </div>
                """, unsafe_allow_html=True)

    # 关键风险与催化剂
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("### ⚠️ 关键风险")
        if key_risks:
            for risk in key_risks:
                st.markdown(f"- 🔴 {risk}")
        else:
            st.info("暂无显著风险信号")
    with col_r2:
        st.markdown("### 🚀 关键催化剂")
        if key_catalysts:
            for cat in key_catalysts:
                st.markdown(f"- 🟢 {cat}")
        else:
            st.info("暂无显著催化剂信号")

    # 评分方法论说明
    with st.expander("📋 评分方法论 · 数据来源 · 评分标准", expanded=False):
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.15);border-radius:8px;padding:1rem;">
            <div style="color:#8892B0;font-size:0.85rem;margin-bottom:0.5rem;">📊 评分模型说明</div>
            <div style="color:#CCD6F6;font-size:0.9rem;margin-bottom:1rem;">{scorecard.get("scoring_summary", "")}</div>
            <div style="color:#8892B0;font-size:0.85rem;margin-bottom:0.5rem;">📡 数据来源</div>
            <div style="color:#CCD6F6;font-size:0.9rem;margin-bottom:1rem;">{scorecard.get("scoring_data_sources", "")}</div>
            <div style="color:#8892B0;font-size:0.85rem;margin-bottom:0.5rem;">📋 评分标准总则</div>
            <div style="color:#6A6D7E;font-size:0.85rem;">{scorecard.get("scoring_criteria", "")}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_kline_tab(stock_input: str):
    """渲染K线技术分析 Tab"""
    st.markdown("### 📈 K线技术分析")

    # 周期选择器
    period_map = {
        "近1月": 30, "近3月": 90, "近6月": 180, "近1年": 365, "近3年": 1095
    }
    col_period, _ = st.columns([2, 4])
    with col_period:
        selected_period = st.selectbox(
            "选择周期", list(period_map.keys()),
            index=1, key="kline_period", label_visibility="collapsed",
        )
    days = period_map[selected_period]

    with st.spinner(f"正在获取 {selected_period} K线数据..."):
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now().replace(year=datetime.now().year - 10)).strftime("%Y%m%d")
            df = MarketDataService.get_stock_history(stock_input.strip(), start_date, end_date)
            if df is not None and not df.empty:
                # 过滤周期
                df = df.tail(days)
                fig = MarketDataService.plot_candlestick(df, stock_input, title=f"{stock_input} - {selected_period} K线图")
                st.plotly_chart(fig, use_container_width=True)

                # 技术指标快照
                indicators = TechnicalIndicators.get_latest_indicators(df)
                signal = TechnicalIndicators.get_market_signal(df)

                st.markdown("### 📊 技术指标快照")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    ma_signal = signal.get("ma_signal", {})
                    st.metric("MA信号", ma_signal.get("signal", "N/A"),
                              ma_signal.get("description", ""))
                with col2:
                    macd = indicators.get("macd", {})
                    st.metric("MACD", macd.get("macd_signal", "N/A"),
                              macd.get("histogram", ""))
                with col3:
                    rsi_val = indicators.get("rsi", {}).get("rsi", "N/A")
                    st.metric("RSI(14)", rsi_val)
                with col4:
                    kdj = indicators.get("kdj", {})
                    st.metric("KDJ", kdj.get("kdj_signal", "N/A"),
                              f"K:{kdj.get('k','')} D:{kdj.get('d','')} J:{kdj.get('j','')}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    bb = indicators.get("bollinger", {})
                    st.metric("布林带位置", bb.get("position", "N/A"),
                              bb.get("width", ""))
                with col2:
                    vol = indicators.get("volume", {})
                    st.metric("成交量", vol.get("volume_ratio", "N/A"),
                              vol.get("volume_ma_status", ""))
                with col3:
                    atr_val = indicators.get("atr", {}).get("atr", "N/A")
                    st.metric("ATR(14)", atr_val)
                with col4:
                    obv_val = indicators.get("obv", {}).get("obv_signal", "N/A")
                    st.metric("OBV", obv_val)

                # 综合信号
                st.markdown("### 🎯 综合技术信号")
                overall = signal.get("overall", {})
                sig = overall.get("signal", "中性")
                sig_color = {"买入": "#00D4AA", "卖出": "#FF4D4D", "中性": "#FFC107"}.get(sig, "#8892B0")
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1.5rem;text-align:center;">
                    <div style="color:#8892B0;font-size:0.85rem;margin-bottom:0.5rem;">综合技术信号</div>
                    <div style="font-size:2rem;font-weight:700;color:{sig_color};">{sig}</div>
                    <div style="color:#6A6D7E;font-size:0.85rem;margin-top:0.5rem;">{overall.get("description", "")}</div>
                    <div style="color:#6A6D7E;font-size:0.75rem;margin-top:0.3rem;">置信度: {overall.get("confidence", "N/A")}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ 未能获取 {stock_input} 的K线数据")
        except Exception as e:
            st.error(f"❌ 获取K线数据失败: {str(e)}")


def _render_fund_flow_tab(market_data: Dict[str, Any]):
    """渲染资金流向分析 Tab"""
    _render_realtime_quote_panel(market_data, "")

    # 资金流向图
    st.markdown("### 💰 资金流向")
    flow_fig = _render_fund_flow_chart(market_data)
    if flow_fig:
        st.plotly_chart(flow_fig, use_container_width=True)
    else:
        st.info("资金流向数据不可用")

    # 沪深港通资金流向
    st.markdown("### 🌐 沪深港通资金流向")
    north_south = market_data.get("north_south_flow", {})
    if north_south:
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            sh_flow = north_south.get("south_bound_sh", north_south.get("sh_flow", "N/A"))
            st.metric("沪股通(南向)", sh_flow)
        with col_n2:
            sz_flow = north_south.get("south_bound_sz", north_south.get("sz_flow", "N/A"))
            st.metric("深股通(南向)", sz_flow)
        with col_n3:
            total = north_south.get("total", north_south.get("total_flow", "N/A"))
            st.metric("合计", total)
    else:
        st.info("沪深港通数据仅在交易时段可用")

    # 融资融券数据
    st.markdown("### 📊 融资融券")
    margin = market_data.get("margin", {})
    if margin:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("融资余额", margin.get("margin_balance", "N/A"))
        with col_m2:
            st.metric("融资买入额", margin.get("margin_buy", "N/A"))
        with col_m3:
            st.metric("融券余额", margin.get("short_balance", "N/A"))
        with col_m4:
            st.metric("融券卖出量", margin.get("short_sell_volume", "N/A"))
    else:
        st.info("融资融券数据仅在交易时段可用")


def render_stock_decode_page():
    """股票深度解码页面（机构级交易终端布局）"""
    st.markdown('<div class="page-header">🔍 股票深度解码</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">机构级多维度分析 — 评分卡 · K线技术分析 · 资金流向 · 深度报告</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ 请先在左侧边栏配置并连接 API")
        return

    # 快速选择栏
    st.markdown(
        '<div class="pro-ticker-bar">'
        '<span style="color:#8892B0;font-size:0.8rem;margin-right:1rem;">🔥 热门:</span>'
        '<span style="margin:0 0.3rem;"><button class="pro-quick-btn" onclick="navigator.clipboard.writeText(\'600519\');alert(\'已复制 600519 (贵州茅台)\')">🇨🇳 贵州茅台</button></span>'
        '<span style="margin:0 0.3rem;"><button class="pro-quick-btn" onclick="navigator.clipboard.writeText(\'AAPL\');alert(\'已复制 AAPL (苹果)\')">🇺🇸 Apple</button></span>'
        '<span style="margin:0 0.3rem;"><button class="pro-quick-btn" onclick="navigator.clipboard.writeText(\'TSLA\');alert(\'已复制 TSLA (特斯拉)\')">🇺🇸 Tesla</button></span>'
        '<span style="margin:0 0.3rem;"><button class="pro-quick-btn" onclick="navigator.clipboard.writeText(\'0700.HK\');alert(\'已复制 0700.HK (腾讯)\')">🇭🇰 腾讯</button></span>'
        '<span style="margin:0 0.3rem;"><button class="pro-quick-btn" onclick="navigator.clipboard.writeText(\'300750\');alert(\'已复制 300750 (宁德时代)\')">🇨🇳 宁德时代</button></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 输入区域
    st.markdown("### 📌 股票查询")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        stock_input = st.text_input(
            "输入股票名称或代码",
            placeholder="例：贵州茅台 / 600519 / AAPL / 0700.HK",
            key="stock_decode_input",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze_btn = st.button("🔍 深度解码", type="primary", use_container_width=True)

    if analyze_btn and stock_input:
        stock_input_clean = stock_input.strip()

        # ===== 第〇步：检测交易时段 =====
        detected_market = RealtimeMarketDataService.detect_market(stock_input_clean)
        market_status = RealtimeMarketDataService.is_market_open(detected_market)
        is_open = market_status["is_open"]

        # 显示市场状态横幅
        status_color = "#00D4AA" if is_open else "#FFC107"
        st.markdown(
            f'<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:0.5rem 1rem;'
            f'margin-bottom:0.5rem;border-left:3px solid {status_color};">'
            f'<span style="color:{status_color};">{market_status["status_text"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ===== 第一步：获取实时市场数据（带超时控制） =====
        market_data = {}
        realtime_data_text = ""
        data_error_msg = ""
        is_fallback = False
        fallback_msg = ""

        with st.spinner("📡 正在获取实时市场数据..."):
            try:
                market_data = RealtimeMarketDataService.get_comprehensive_market_data(stock_input_clean)
                realtime_data_text = RealtimeMarketDataService.format_market_data_for_prompt(market_data)
                quote_err = market_data.get("quote", {}).get("error", "")
                if quote_err:
                    data_error_msg = f"行情接口: {quote_err}"
            except Exception as e:
                err_str = str(e)
                if "SSL" in err_str or "DECRYPTION" in err_str:
                    data_error_msg = "数据源（东方财富）SSL 连接异常，可能是网络环境问题"
                else:
                    data_error_msg = f"数据获取异常: {err_str}"

        # ===== 第二步：检查数据是否有效，无效则自动降级到历史数据 =====
        has_valid_data = bool(
            market_data.get("quote", {}).get("price")
            or market_data.get("technical", {}).get("ma5")
            or market_data.get("fund_flow", {}).get("main_net_inflow")
        )

        if not has_valid_data:
            # 自动降级：用历史K线数据生成兜底数据
            with st.spinner("📊 实时数据不可用，正在基于历史K线数据生成分析..."):
                fallback_data = RealtimeMarketDataService.generate_fallback_from_history(stock_input_clean)
                if fallback_data.get("quote") and fallback_data.get("technical"):
                    # 合并兜底数据到 market_data（保留已有的任何数据）
                    if not market_data.get("quote"):
                        market_data["quote"] = fallback_data["quote"]
                    if not market_data.get("technical"):
                        market_data["technical"] = fallback_data["technical"]
                    market_data["_fallback"] = True
                    is_fallback = True
                    fallback_msg = fallback_data.get("_fallback_message", "使用历史K线数据替代实时数据")
                    # 重新生成 prompt 文本
                    realtime_data_text = RealtimeMarketDataService.format_market_data_for_prompt(market_data)
                    has_valid_data = True
                    data_error_msg = ""  # 清除之前的错误信息
                else:
                    fallback_err = fallback_data.get("_fallback_error", "无法获取历史数据")
                    if not data_error_msg:
                        data_error_msg = f"实时数据和历史数据均获取失败: {fallback_err}"

        # ===== 第三步：评分引擎计算（基于真实数据，不依赖 AI） =====
        scorecard = {}
        if has_valid_data:
            try:
                scorecard = ScoringEngine.calculate_all_scores(market_data)
                # 如果是兜底数据，在评分卡中标记
                if is_fallback:
                    scorecard["_fallback"] = True
                    scorecard["_fallback_message"] = fallback_msg
            except Exception as e:
                st.warning(f"⚠️ 评分引擎计算异常: {str(e)}")

        # ===== 第四步：AI 深度分析（使用流式加载，先显示评分和K线） =====
        ai_result = {}
        with st.spinner("🔄 AI 正在基于实时数据进行深度分析，请稍候..."):
            try:
                if not st.session_state.api_client:
                    st.error("⚠️ 请先在侧边栏配置 API 密钥")
                    return
                prompt_template = PromptManager.get_prompt("stock_deep_decode")
                filled_prompt = prompt_template.format(
                    user_stock_input=stock_input,
                    realtime_market_data=realtime_data_text,
                )
                result_text = st.session_state.api_client.analyze_stock_deep_decode(
                    stock_input, filled_prompt
                )
                ai_result = parse_json_response(result_text)

                if "error" in ai_result:
                    st.error(f"❌ AI 分析失败: {ai_result['error']}")
                    if "raw_content" in ai_result:
                        with st.expander("查看原始返回内容"):
                            st.text(ai_result["raw_content"])
                    # AI 失败不阻断，继续显示评分和K线
            except Exception as e:
                st.warning(f"⚠️ AI 分析异常: {str(e)}，评分和K线分析仍可用")

        # ===== 保存历史 =====
        combined_result = {**ai_result, "_scorecard": scorecard, "_market_data": market_data}
        st.session_state.analysis_history.append({
            "type": "stock_deep_decode",
            "input": stock_input,
            "result": combined_result,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # ===== Tab 布局 =====
        tab1, tab2, tab3, tab4 = st.tabs(["📊 综合评分仪表盘", "📈 K线技术分析", "💰 资金流向分析", "📋 深度分析报告"])

        with tab1:
            if data_error_msg and not is_fallback:
                st.error(f"❌ {data_error_msg}")
            if is_fallback:
                st.info(f"ℹ️ {fallback_msg}")
            if scorecard:
                _render_score_dashboard(scorecard, market_data)
            elif not data_error_msg:
                st.warning("⚠️ 评分数据不可用，请检查市场数据是否获取成功")

        with tab2:
            _render_kline_tab(stock_input)

        with tab3:
            if market_data and not is_fallback:
                _render_fund_flow_tab(market_data)
            elif is_fallback:
                st.info("ℹ️ 当前使用历史K线数据，资金流向数据仅在实时数据可用时展示")
            else:
                st.info("市场数据不可用，无法展示资金流向分析")

        with tab4:
            if ai_result and "error" not in ai_result:
                render_stock_decode_result(ai_result)
            else:
                st.warning("AI 分析结果不可用")

    elif analyze_btn:
        st.warning("⚠️ 请输入股票名称或代码")


# ============================================================
def render_stock_comparison_result(result: Dict[str, Any]):
    """渲染多股票对比分析结果"""
    if "comparison_table" not in result:
        st.warning("⚠️ 对比数据缺失，显示已有内容")

    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    table = result.get("comparison_table", [])
    if table and isinstance(table, list):
        st.markdown("## 📊 多股票横向对比")
        st.markdown("---")

        if table:
            headers = list(table[0].keys())
            header_labels = {
                "stock_name": "股票名称", "stock_code": "代码", "market": "所属市场",
                "exchange": "交易所", "sector": "行业板块", "price_limit": "涨跌幅限制",
                "settlement": "结算方式", "short_selling": "融券做空",
                "min_tick": "最小变动单位", "listing_requirements": "上市制度",
                "regulator": "监管机构", "investor_threshold": "投资者门槛",
            }

            table_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
            table_html += '<thead><tr>'
            for h in headers:
                label = header_labels.get(h, h)
                table_html += f'<th style="background:#1A1D27;color:#00D4AA;padding:10px 8px;border:1px solid #2A2D3E;text-align:left;white-space:nowrap;">{label}</th>'
            table_html += '</tr></thead><tbody>'

            for row in table:
                table_html += '<tr>'
                for h in headers:
                    val = row.get(h, "")
                    table_html += f'<td style="padding:8px;border:1px solid #2A2D3E;color:#E8E8E8;">{val}</td>'
                table_html += '</tr>'
            table_html += '</tbody></table>'

            st.markdown(table_html, unsafe_allow_html=True)

    diffs = result.get("key_differences", [])
    if diffs and isinstance(diffs, list):
        st.markdown("### 🔑 关键差异点")
        for d in diffs:
            st.markdown(
                f'<div style="margin:0.5rem 0;padding:0.75rem;background:rgba(0,163,255,0.05);'
                f'border-radius:8px;border-left:3px solid #00A3FF;color:#E8E8E8;">{d}</div>',
                unsafe_allow_html=True,
            )

    arb = result.get("cross_market_arbitrage", "")
    if arb:
        st.markdown("### 🔄 跨市场套利机会")
        st.markdown(
            f'<div class="result-section" style="border-left-color:#FF9800;">'
            f'<div class="result-value">{arb}</div></div>',
            unsafe_allow_html=True,
        )

    strategy = result.get("investment_strategy", "")
    if strategy:
        st.markdown("### 💡 投资策略建议")
        st.markdown(
            f'<div class="result-section" style="border-left-color:#00D4AA;">'
            f'<div class="result-value">{strategy}</div></div>',
            unsafe_allow_html=True,
        )

    risks = result.get("risk_warnings", [])
    if risks and isinstance(risks, list):
        st.markdown("### ⚠️ 风险提示")
        for risk in risks:
            st.markdown(
                f'<span class="tag tag-risk">⚠</span> '
                f'<span style="color: #E8E8E8;">{risk}</span><br>',
                unsafe_allow_html=True,
            )

    disclaimer = result.get("disclaimer", "")
    if disclaimer:
        st.markdown("---")
        st.markdown(
            f'<div style="background:rgba(255,152,0,0.1);border:1px solid rgba(255,152,0,0.3);'
            f'border-radius:8px;padding:1rem;margin-top:1rem;">'
            f'<div style="color:#FF9800;font-weight:600;margin-bottom:0.5rem;">⚠️ 免责声明</div>'
            f'<div style="color:#E8E8E8;font-size:0.85rem;">{disclaimer}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    _render_export_buttons(result, "stock_comparison")


def render_stock_comparison_page():
    """多股票对比分析页面"""
    st.markdown('<div class="page-header">📊 多股票对比分析</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">输入多只股票代码或名称，AI 横向对比市场归属、交易规则、估值等</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ 请先在左侧边栏配置并连接 API")
        return

    st.markdown("### 📌 股票列表")
    stock_input = st.text_area(
        "输入多只股票名称或代码，用逗号、空格或换行分隔",
        height=120,
        placeholder="例：贵州茅台, 腾讯控股, AAPL\n或：600519, 0700.HK, AAPL\n或：贵州茅台 腾讯控股 AAPL TSLA",
        key="comparison_input",
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button(
            "📊 开始对比分析",
            type="primary",
            use_container_width=True,
        )

    if analyze_btn and stock_input.strip():
        with st.spinner("🔄 AI 正在对比分析，请稍候..."):
            try:
                if not st.session_state.api_client:
                    st.error("⚠️ 请先在侧边栏配置 API 密钥")
                    return
                prompt_template = PromptManager.get_prompt("stock_comparison")
                result_text = st.session_state.api_client.analyze_stock_comparison(
                    stock_input.strip(), prompt_template
                )
                result = parse_json_response(result_text)

                if "error" in result:
                    st.error(f"❌ 分析失败: {result['error']}")
                    if "raw_content" in result:
                        with st.expander("查看原始返回内容"):
                            st.text(result["raw_content"])
                else:
                    st.session_state.analysis_history.append({
                        "type": "stock_comparison",
                        "input": stock_input.strip()[:100] + "...",
                        "result": result,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

                    render_stock_comparison_result(result)

            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")

    elif analyze_btn:
        st.warning("⚠️ 请输入至少两只股票名称或代码")


def render_history_page():
    """历史记录页面"""
    st.markdown('<div class="page-header">📚 分析历史</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">查看本次会话的所有分析记录</div>',
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
            "stock_comparison": "📊",
        }
        icon = type_icons.get(record["type"], "📄")

        with st.expander(f"{icon} {record['time']} - {record['input']}"):
            render_analysis_result(record["result"], record["type"])


# ============================================================
# 主函数
# ============================================================
def main():
    """应用主入口"""
    init_session_state()
    load_css()

    render_sidebar()

    # 顶部导航栏
    api_status = "online" if st.session_state.api_configured else "offline"
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-brand">
            <div class="topbar-logo">AI</div>
            <div class="topbar-title">Financial <span>Insight</span></div>
            <span class="topbar-version">v2.0.0</span>
        </div>
        <div class="topbar-status">
            <span><span class="status-dot {api_status}"></span>API</span>
            <span>{datetime.now().strftime('%H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    page_handlers = {
        "news_analysis": render_news_analysis_page,
        "announcement_analysis": render_announcement_analysis_page,
        "hotspot_analysis": render_hotspot_analysis_page,
        "stock_deep_decode": render_stock_decode_page,
        "stock_comparison": render_stock_comparison_page,
    }

    handler = page_handlers.get(st.session_state.current_page)
    if handler:
        handler()

    st.markdown("---")
    st.markdown("""
    <div class="app-footer">
        <div>AI Financial Insight Assistant</div>
        <div>本工具提供的分析仅供参考，不构成投资建议 · 投资有风险，决策需谨慎</div>
        <div>Powered by Streamlit + AI API</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()