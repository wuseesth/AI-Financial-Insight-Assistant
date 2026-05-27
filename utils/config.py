"""
配置文件
========
管理应用配置，支持环境变量和页面设置。
"""

import os
from typing import Dict, Any


class AppConfig:
    """应用配置管理"""

    # 应用基本信息
    APP_TITLE = "AI 金融信息分析助手"
    APP_SUBTITLE = "AI Financial Insight Assistant"
    APP_ICON = "📈"
    APP_LAYOUT = "wide"

    # 页面配置
    PAGE_CONFIG = {
        "page_title": f"{APP_ICON} {APP_TITLE}",
        "page_icon": APP_ICON,
        "layout": APP_LAYOUT,
        "initial_sidebar_state": "expanded",
    }

    # API 默认配置
    DEFAULT_BACKEND = "deepseek"
    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 4096

    # 样式配置
    THEME = {
        "primaryColor": "#00D4AA",
        "backgroundColor": "#0E1117",
        "secondaryBackgroundColor": "#1A1D27",
        "textColor": "#E8E8E8",
        "font": "sans serif",
    }

    # 功能模块配置
    MODULES = {
        "news_analysis": {
            "name": "📰 财经新闻分析",
            "icon": "📰",
            "description": "对财经新闻进行自动总结、利好利空分析",
            "enabled": True,
        },
        "announcement_analysis": {
            "name": "📋 上市公司公告分析",
            "icon": "📋",
            "description": "分析上市公司公告，提取核心事件和财务数据",
            "enabled": True,
        },
        "hotspot_analysis": {
            "name": "🔥 市场热点分析",
            "icon": "🔥",
            "description": "提取市场热点、热门行业和公司",
            "enabled": True,
        },
    }

    @classmethod
    def get_env_api_key(cls, backend: str = "deepseek") -> str:
        """从环境变量获取 API Key"""
        if backend == "deepseek":
            return os.getenv("DEEPSEEK_API_KEY", "")
        return os.getenv("OPENAI_API_KEY", "")

    @classmethod
    def has_api_key(cls, backend: str = "deepseek") -> bool:
        """检查是否有可用的 API Key"""
        return bool(cls.get_env_api_key(backend))

    @classmethod
    def get_module_config(cls, module_name: str) -> Dict[str, Any]:
        """获取模块配置"""
        return cls.MODULES.get(module_name, {})

    @classmethod
    def get_enabled_modules(cls) -> Dict[str, Any]:
        """获取已启用的模块"""
        return {
            name: config
            for name, config in cls.MODULES.items()
            if config["enabled"]
        }
