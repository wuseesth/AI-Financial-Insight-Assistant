"""
API 客户端模块
==============
封装大模型 API 调用逻辑，支持 OpenAI 和 DeepSeek 等多种后端。
支持后续扩展为 Agent 调用或 RAG 检索增强生成。
"""

import os
import json
import time
from typing import Optional, List, Dict, Any
from openai import OpenAI, APIError, RateLimitError, APITimeoutError


# 支持的 API 后端配置
API_BACKENDS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
}


class APIClient:
    """大模型 API 客户端，支持多后端切换"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        backend: str = "deepseek",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        初始化 API 客户端

        Args:
            api_key: API 密钥，默认从环境变量读取
            backend: 后端类型 ("openai" 或 "deepseek")
            model: 模型名称，默认使用各后端推荐模型
            base_url: 自定义 API 地址
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.backend = backend.lower()
        self.max_retries = max_retries
        self.timeout = timeout

        # 从环境变量获取 API Key
        if not api_key:
            if self.backend == "deepseek":
                api_key = os.getenv("DEEPSEEK_API_KEY", "")
            else:
                api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key:
            raise ValueError(
                f"未找到 {self.backend} API Key，请设置环境变量 "
                f"{'DEEPSEEK_API_KEY' if self.backend == 'deepseek' else 'OPENAI_API_KEY'}"
                f" 或在页面中手动输入。"
            )

        # 确定 base_url
        if not base_url:
            base_url = API_BACKENDS.get(self.backend, {}).get("base_url", "")

        # 确定模型
        if not model:
            model = (
                "deepseek-chat"
                if self.backend == "deepseek"
                else "gpt-4o-mini"
            )
        self.model = model

        # 初始化 OpenAI 客户端（兼容 DeepSeek）
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数 (0-2)
            max_tokens: 最大输出 token 数
            stream: 是否流式输出

        Returns:
            模型返回的文本内容
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                )

                if stream:
                    # 流式输出处理
                    full_content = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_content += chunk.choices[0].delta.content
                    return full_content
                else:
                    return response.choices[0].message.content or ""

            except RateLimitError as e:
                last_error = e
                wait_time = (attempt + 1) * 2
                time.sleep(wait_time)

            except APITimeoutError as e:
                last_error = e
                time.sleep(1)

            except APIError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)

            except Exception as e:
                last_error = e
                break

        error_msg = f"API 调用失败（已重试 {self.max_retries} 次）: {last_error}"
        raise RuntimeError(error_msg)

    def analyze_financial_news(self, news_text: str, prompt_template: str) -> str:
        """
        分析财经新闻

        Args:
            news_text: 财经新闻文本
            prompt_template: 分析提示词模板

        Returns:
            分析结果
        """
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的金融分析师，擅长分析财经新闻并给出专业见解。",
            },
            {
                "role": "user",
                "content": prompt_template.format(news_text=news_text),
            },
        ]
        return self.chat(messages, temperature=0.3, max_tokens=4096)

    def analyze_announcement(self, announcement_text: str, prompt_template: str) -> str:
        """
        分析上市公司公告

        Args:
            announcement_text: 公告文本
            prompt_template: 分析提示词模板

        Returns:
            分析结果
        """
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的证券分析师，擅长分析上市公司公告并提取关键信息。",
            },
            {
                "role": "user",
                "content": prompt_template.format(announcement_text=announcement_text),
            },
        ]
        return self.chat(messages, temperature=0.3, max_tokens=4096)

    def analyze_hotspots(self, news_list: str, prompt_template: str) -> str:
        """
        分析市场热点

        Args:
            news_list: 多条新闻列表
            prompt_template: 分析提示词模板

        Returns:
            热点分析结果
        """
        messages = [
            {
                "role": "system",
                "content": "你是一位资深市场分析师，擅长从大量信息中提取市场热点和趋势。",
            },
            {
                "role": "user",
                "content": prompt_template.format(news_list=news_list),
            },
        ]
        return self.chat(messages, temperature=0.4, max_tokens=4096)


def get_available_backends() -> List[str]:
    """获取可用的 API 后端列表"""
    return list(API_BACKENDS.keys())


def get_backend_models(backend: str) -> List[str]:
    """获取指定后端的可用模型列表"""
    return API_BACKENDS.get(backend.lower(), {}).get("models", [])
