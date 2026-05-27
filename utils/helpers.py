"""
辅助工具函数
===========
提供格式化、缓存、日志等通用功能。
"""

import json
import re
import hashlib
import time
from typing import Any, Dict, Optional
from pathlib import Path


def parse_json_response(response: str) -> Dict[str, Any]:
    """
    解析 API 返回的 JSON 字符串，支持多种格式

    Args:
        response: API 返回的原始字符串

    Returns:
        解析后的字典
    """
    if not response:
        return {"error": "返回内容为空"}

    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 代码块（```json ... ```）
    json_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试提取最外层大括号内容
    brace_pattern = r"\{[\s\S]*\}"
    match = re.search(brace_pattern, response)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"error": "无法解析返回内容", "raw_content": response[:500]}


def format_currency(value: float, unit: str = "元") -> str:
    """
    格式化货币数值

    Args:
        value: 数值
        unit: 单位

    Returns:
        格式化后的字符串
    """
    if value >= 1e8:
        return f"{value / 1e8:.2f}亿{unit}"
    elif value >= 1e4:
        return f"{value / 1e4:.2f}万{unit}"
    else:
        return f"{value:.2f}{unit}"


def format_percentage(value: float) -> str:
    """格式化百分比"""
    return f"{value:+.2f}%" if value != 0 else "0.00%"


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本并添加省略号"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def safe_get(data: Dict, *keys, default: Any = "") -> Any:
    """
    安全获取嵌套字典的值

    Args:
        data: 字典数据
        keys: 键路径
        default: 默认值

    Returns:
        获取到的值或默认值
    """
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data if data is not None else default


class SimpleCache:
    """简单的内存缓存实现"""

    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: 缓存生存时间（秒），默认5分钟
        """
        self._cache: Dict[str, tuple] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存值"""
        self._cache[key] = (value, time.time())

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        content = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(content.encode()).hexdigest()


# 全局缓存实例
cache = SimpleCache(ttl=300)


def ensure_data_dir():
    """确保数据目录存在"""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir
