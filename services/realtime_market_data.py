"""
实时市场数据聚合服务
====================
基于 AKShare + 新浪财经备用接口，聚合多维度实时市场数据。
为 AI 分析提供真实的量化数据支撑，替代模型知识猜测。

支持的数据维度：
1. 实时行情快照（最新价、涨跌幅、成交量等）
2. 个股资金流向（主力/超大单/大单/中单/小单）
3. 沪深港通资金流向（北向/南向）
4. 融资融券余额
5. 龙虎榜数据
6. 板块资金流向
7. 实时新闻舆情
8. 技术指标（复用 TechnicalIndicators）

数据源说明：
- 主数据源：AKShare（东方财富接口）
- 备用数据源：新浪财经 API（纯 HTTP，无 SSL 问题）
- 兜底方案：历史 K 线数据（当所有实时接口都失败时）
"""

import json
import time
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from services.market_data import MarketDataService
from services.technical_indicators import TechnicalIndicators


class RealtimeMarketDataService:
    """实时市场数据聚合服务"""

    # 美股列表（用于判断市场）
    US_STOCKS = {"AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA",
                 "AMD", "BABA", "JD", "BIDU", "NFLX", "GOOG", "QQQ", "SPY"}

    # ========== 内存缓存 ==========
    _CACHE: Dict[str, Dict[str, Any]] = {}
    _CACHE_TTL: Dict[str, float] = {}  # key -> expiry timestamp
    _CACHE_DURATION = {
        "quote": 10,          # 实时行情：10秒
        "technical": 30,      # 技术指标：30秒
        "fund_flow": 60,      # 资金流向：60秒
        "margin": 120,        # 融资融券：2分钟
        "north_south": 300,   # 沪深港通：5分钟
        "sector": 300,        # 板块资金流向：5分钟
        "hot_rank": 120,      # 热度排名：2分钟
        "news": 120,          # 个股新闻：2分钟
    }

    # ========== 交易时段定义 ==========
    # A股：周一至周五 9:30-11:30, 13:00-15:00
    # 港股：周一至周五 9:30-12:00, 13:00-16:00
    # 美股：周一至周五 9:30-16:00 ET (夏令时 21:30-04:00, 冬令时 22:30-05:00 北京时间)
    MARKET_HOURS = {
        "a": {
            "name": "A股",
            "sessions": [
                ("09:30", "11:30"),
                ("13:00", "15:00"),
            ],
            "timezone": "Asia/Shanghai",
        },
        "hk": {
            "name": "港股",
            "sessions": [
                ("09:30", "12:00"),
                ("13:00", "16:00"),
            ],
            "timezone": "Asia/Shanghai",
        },
        "us": {
            "name": "美股",
            "sessions": [
                ("09:30", "16:00"),  # ET 时间
            ],
            "timezone": "US/Eastern",
        },
    }

    @staticmethod
    def is_market_open(market: str = "a") -> Dict[str, Any]:
        """
        判断指定市场当前是否在交易时段

        Returns:
            {"is_open": bool, "next_open": str, "next_close": str, "status_text": str}
        """
        now = datetime.now()
        weekday = now.weekday()  # 0=周一, 6=周日

        # 周末休市
        if weekday >= 5:
            next_monday = now + timedelta(days=(7 - weekday))
            next_open_str = next_monday.strftime("%Y-%m-%d") + " 09:30"
            return {
                "is_open": False,
                "next_open": next_open_str,
                "next_close": "",
                "status_text": f"📅 今天是周末（{'周六' if weekday == 5 else '周日'}），{RealtimeMarketDataService.MARKET_HOURS.get(market, {}).get('name', '该市场')}休市。下一交易日：{next_open_str}",
            }

        market_info = RealtimeMarketDataService.MARKET_HOURS.get(market, RealtimeMarketDataService.MARKET_HOURS["a"])
        current_time_str = now.strftime("%H:%M")

        for session_start, session_end in market_info["sessions"]:
            if session_start <= current_time_str <= session_end:
                return {
                    "is_open": True,
                    "next_open": "",
                    "next_close": session_end,
                    "status_text": f"🟢 {market_info['name']}交易中（{session_start}-{session_end}）",
                }

        # 非交易时段：找出下一个开盘时间
        # 先找今天是否还有未开始的交易时段
        for session_start, session_end in market_info["sessions"]:
            if current_time_str < session_start:
                return {
                    "is_open": False,
                    "next_open": f"{now.strftime('%Y-%m-%d')} {session_start}",
                    "next_close": session_end,
                    "status_text": f"⏸️ {market_info['name']}已休市（今日交易时段：{market_info['sessions'][0][0]}-{market_info['sessions'][-1][1]}），下一交易时段：{session_start}",
                }

        # 今天所有交易时段已过，下一交易日
        next_day = now + timedelta(days=1)
        # 如果明天是周末，跳到周一
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        next_open_str = f"{next_day.strftime('%Y-%m-%d')} {market_info['sessions'][0][0]}"
        return {
            "is_open": False,
            "next_open": next_open_str,
            "next_close": market_info['sessions'][0][1],
            "status_text": f"⏸️ {market_info['name']}今日已收盘。下一交易日：{next_open_str}",
        }

    @staticmethod
    def generate_fallback_from_history(symbol: str) -> Dict[str, Any]:
        """
        当实时数据获取失败时，基于历史K线数据生成兜底评分数据

        从历史行情中提取：
        - 最新价格、涨跌幅
        - 均线系统（MA5/10/20/60）
        - 技术指标（MACD/RSI/KDJ）
        - 波动率
        - 成交量/换手率估算

        Returns:
            与 get_comprehensive_market_data 兼容的数据字典
        """
        data = {
            "symbol": symbol,
            "market": RealtimeMarketDataService.detect_market(symbol),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_fallback": True,  # 标记为兜底数据
            "_fallback_message": "⚠️ 实时数据获取失败，已自动降级使用历史K线数据进行分析。评分基于历史技术指标，不包含实时行情和资金流向。",
        }

        try:
            service = MarketDataService()
            df = service.get_stock_history(symbol=symbol, period="1y")
            if df is None or df.empty:
                data["_fallback_error"] = "无法获取历史K线数据"
                return data

            # 计算技术指标
            indicators_df = TechnicalIndicators.calc_all_indicators(df)
            latest_indicators = TechnicalIndicators.get_latest_indicators(indicators_df)
            signal = TechnicalIndicators.get_market_signal(indicators_df)

            # 从历史数据构建 quote 数据
            last_row = df.iloc[-1]
            close_series = df["close"]
            volume_series = df["volume"]

            # 估算换手率（如果没有换手率列，用成交量/流通股本估算）
            turnover_est = None
            if "turnover" in df.columns:
                turnover_est = float(last_row.get("turnover", 0))
            elif "amount" in df.columns and "close" in df.columns:
                # 粗略估算：成交额/（收盘价*流通股本），这里用成交量代替
                pass

            # 构建 quote 子集
            quote = {
                "name": symbol,
                "price": float(last_row.get("close", 0)),
                "change": float(last_row.get("change", last_row.get("close", 0) - df.iloc[-2].get("close", 0) if len(df) > 1 else 0)),
                "pct_change": float(last_row.get("pct_change", 0)),
                "volume": float(last_row.get("volume", 0)),
                "amount": float(last_row.get("amount", 0)),
                "turnover": turnover_est,
                "high": float(last_row.get("high", 0)),
                "low": float(last_row.get("low", 0)),
                "open": float(last_row.get("open", 0)),
                "pre_close": float(df.iloc[-2].get("close", 0)) if len(df) > 1 else float(last_row.get("close", 0)),
                "market": RealtimeMarketDataService.detect_market(symbol),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "_from_history": True,
            }

            # 构建 technical 子集
            technical = {
                "latest_price": float(last_row["close"]),
                "ma5": float(close_series.rolling(5).mean().iloc[-1]) if len(df) >= 5 else None,
                "ma10": float(close_series.rolling(10).mean().iloc[-1]) if len(df) >= 10 else None,
                "ma20": float(close_series.rolling(20).mean().iloc[-1]) if len(df) >= 20 else None,
                "ma60": float(close_series.rolling(60).mean().iloc[-1]) if len(df) >= 60 else None,
                "ma120": float(close_series.rolling(120).mean().iloc[-1]) if len(df) >= 120 else None,
                "volume_ma5": float(volume_series.rolling(5).mean().iloc[-1]) if len(df) >= 5 else None,
                "volume_ma20": float(volume_series.rolling(20).mean().iloc[-1]) if len(df) >= 20 else None,
                "latest_volume": float(last_row["volume"]),
                "high_52w": float(df["high"].max()),
                "low_52w": float(df["low"].min()),
                "pct_change_1d": float(close_series.pct_change().iloc[-1] * 100) if len(df) > 1 else 0,
                "pct_change_5d": float((close_series.iloc[-1] / close_series.iloc[-5] - 1) * 100) if len(df) >= 5 else 0,
                "pct_change_20d": float((close_series.iloc[-1] / close_series.iloc[-20] - 1) * 100) if len(df) >= 20 else 0,
                "volatility_20d": float(close_series.pct_change().rolling(20).std().iloc[-1] * 100) if len(df) >= 20 else 0,
                "signal": signal,
                "indicators": latest_indicators,
                "_from_history": True,
            }

            # 判断均线排列
            ma5 = technical["ma5"]
            ma10 = technical["ma10"]
            ma20 = technical["ma20"]
            ma60 = technical["ma60"]
            if all(v is not None for v in [ma5, ma10, ma20, ma60]):
                if ma5 > ma10 > ma20 > ma60:
                    technical["ma_status"] = "多头排列"
                elif ma5 < ma10 < ma20 < ma60:
                    technical["ma_status"] = "空头排列"
                else:
                    technical["ma_status"] = "缠绕震荡"
            else:
                technical["ma_status"] = "数据不足"

            data["quote"] = quote
            data["technical"] = technical

        except Exception as e:
            data["_fallback_error"] = str(e)

        return data

    @classmethod
    def _get_cache(cls, key: str) -> Optional[Any]:
        """获取缓存（如果未过期）"""
        expiry = cls._CACHE_TTL.get(key, 0)
        if time.time() < expiry and key in cls._CACHE:
            return cls._CACHE[key]
        return None

    @classmethod
    def _set_cache(cls, key: str, value: Any, duration: int = 60):
        """设置缓存"""
        cls._CACHE[key] = value
        cls._CACHE_TTL[key] = time.time() + duration

    @staticmethod
    def detect_market(symbol: str) -> str:
        """检测股票所属市场"""
        s = symbol.strip().upper()
        if s.endswith(".HK"):
            return "hk"
        # 美股判断：必须是纯英文字母且长度<=5（美股代码特征），且不能包含中文字符
        if s in RealtimeMarketDataService.US_STOCKS or (s.isascii() and s.isalpha() and len(s) <= 5):
            return "us"
        return "a"

    @staticmethod
    def get_stock_basic_info(symbol: str) -> Dict[str, Any]:
        """
        获取股票基础信息 - 永远可用，不依赖任何外部接口

        通过代码规则推断市场和板块：
        - 600/601/603/605 → 沪市主板
        - 000/001/002 → 深市主板
        - 300/301 → 创业板
        - 688 → 科创板
        - 8/4开头 → 北交所
        - 字母+数字 → 美股
        - 数字.HK → 港股
        """
        market = RealtimeMarketDataService.detect_market(symbol)
        clean = symbol.replace(".HK", "").replace(".", "").upper()

        info = {
            "symbol": symbol,
            "market": market,
            "market_name": {"a": "A股", "hk": "港股", "us": "美股"}.get(market, "未知"),
            "board": "未知",
            "board_desc": "",
        }

        if market == "a":
            if clean.startswith(("600", "601", "603", "605")):
                info["board"] = "主板"
                info["board_desc"] = "沪市主板"
            elif clean.startswith(("000", "001", "002")):
                info["board"] = "主板"
                info["board_desc"] = "深市主板"
            elif clean.startswith(("300", "301")):
                info["board"] = "创业板"
                info["board_desc"] = "深市创业板"
            elif clean.startswith("688"):
                info["board"] = "科创板"
                info["board_desc"] = "沪市科创板"
            elif clean.startswith(("8", "4")):
                info["board"] = "北交所"
                info["board_desc"] = "北京证券交易所"
        elif market == "hk":
            info["board"] = "主板"
            info["board_desc"] = "香港交易所主板"
        elif market == "us":
            info["board"] = "美股"
            info["board_desc"] = "NASDAQ / NYSE"

        return info

    @staticmethod
    def _fetch_sina_quote(symbol: str) -> Optional[Dict[str, Any]]:
        """
        备用方案：通过新浪财经 API 获取实时行情（纯 HTTP，无 SSL 问题）

        新浪接口格式（A股）：
        var hq_str_sh600513="联环药业,16.880,16.880,16.890,17.100,16.700,16.890,16.900,...
        字段顺序：名称,今开,昨收,当前价,最高,最低,买入价,卖出价,成交量,成交额,...
        """
        try:
            market = RealtimeMarketDataService.detect_market(symbol)
            sina_symbol = symbol.replace(".HK", "").replace(".", "")

            # 新浪前缀规则
            if market == "a":
                # A 股：sh=上海, sz=深圳, bj=北京
                if symbol.startswith("6"):
                    sina_code = f"sh{sina_symbol}"
                elif symbol.startswith("0") or symbol.startswith("3"):
                    sina_code = f"sz{sina_symbol}"
                elif symbol.startswith("8") or symbol.startswith("4"):
                    sina_code = f"bj{sina_symbol}"
                else:
                    sina_code = f"sh{sina_symbol}"
            elif market == "hk":
                sina_code = f"hk{sina_symbol}"
            elif market == "us":
                # 美股用新浪的 gp 前缀
                sina_code = f"gb_{sina_symbol}"
            else:
                return None

            url = f"https://hq.sinajs.cn/list={sina_code}"
            headers = {
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10, verify=False)
            resp.encoding = "gbk"

            if not resp.text or "hq_str" not in resp.text:
                return None

            # 解析新浪返回数据
            text = resp.text.strip()
            # 格式: var hq_str_sh600513="名称,今开,昨收,当前价,最高,最低,...";
            match = re.search(r'"([^"]+)"', text)
            if not match:
                return None

            parts = match.group(1).split(",")
            if len(parts) < 30:
                return None

            # 新浪 A 股字段索引
            name = parts[0]
            open_price = float(parts[1]) if parts[1] else 0
            pre_close = float(parts[2]) if parts[2] else 0
            price = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            volume = float(parts[8]) if parts[8] else 0  # 手
            amount = float(parts[9]) if parts[9] else 0   # 万
            # 成交量转股（A股1手=100股）
            volume_shares = volume * 100
            # 成交额转元
            amount_yuan = amount * 10000

            change = price - pre_close
            pct_change = (change / pre_close * 100) if pre_close != 0 else 0

            # 换手率新浪不直接提供，用成交额估算
            turnover = None

            result = {
                "name": name,
                "price": price,
                "change": round(change, 3),
                "pct_change": round(pct_change, 2),
                "volume": volume_shares,
                "amount": amount_yuan,
                "turnover": turnover,
                "high": high,
                "low": low,
                "open": open_price,
                "pre_close": pre_close,
                "market": "A股" if market == "a" else ("港股" if market == "hk" else "美股"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "_source": "sina_finance",
            }
            return result

        except Exception as e:
            return None

    @staticmethod
    def _fetch_tencent_quote(symbol: str) -> Optional[Dict[str, Any]]:
        """
        腾讯财经 API - 纯 HTTP，国内访问最快，数据最丰富

        接口: https://qt.gtimg.cn/q=sh600513
        返回格式: v_sh600513="1~联环药业~16.880~16.890~..."

        字段索引说明:
        1=名称, 2=代码, 3=最新价, 4=昨收, 5=今开,
        6=成交量(手), 7=成交额, 8=最高, 9=最低,
        32=换手率, 39=市盈率, 44=总市值, 45=流通市值
        """
        try:
            market = RealtimeMarketDataService.detect_market(symbol)
            clean = symbol.replace(".HK", "").replace(".", "")

            # 腾讯前缀规则
            prefix_map = {
                "a": "sh",
                "hk": "hk",
                "us": "us",
            }
            # A 股细分：上海/深圳/北京
            if market == "a":
                if clean.startswith(("6", "9")):
                    prefix = "sh"
                elif clean.startswith(("0", "3", "2")):
                    prefix = "sz"
                elif clean.startswith(("8", "4")):
                    prefix = "bj"
                else:
                    prefix = "sh"
            else:
                prefix = prefix_map.get(market, "sh")

            tencent_code = f"{prefix}{clean}"
            url = f"https://qt.gtimg.cn/q={tencent_code}"

            resp = requests.get(url, timeout=5)
            resp.encoding = "gbk"

            if not resp.text:
                return None

            # 解析返回数据: v_sh600513="1~联环药业~16.880~..."
            match = re.search(r'"(.*?)"', resp.text)
            if not match:
                return None

            fields = match.group(1).split("~")
            if len(fields) < 10:
                return None

            name = fields[1]
            price = float(fields[3]) if fields[3] else 0
            pre_close = float(fields[4]) if fields[4] else 0
            open_p = float(fields[5]) if fields[5] else 0
            volume_hand = float(fields[6]) if fields[6] else 0  # 手
            amount_yuan = float(fields[7]) if fields[7] else 0   # 元
            high = float(fields[8]) if fields[8] else 0
            low = float(fields[9]) if fields[9] else 0

            # 腾讯字段索引 32=换手率%, 39=市盈率, 44=总市值, 45=流通市值
            turnover = fields[32] if len(fields) > 32 and fields[32] else None
            pe = fields[39] if len(fields) > 39 and fields[39] else None
            market_cap = fields[44] if len(fields) > 44 and fields[44] else None
            circ_cap = fields[45] if len(fields) > 45 and fields[45] else None

            change = price - pre_close
            pct_change = (change / pre_close * 100) if pre_close else 0
            volume = volume_hand * 100  # 手转股

            result = {
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "pct_change": round(pct_change, 2),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "pre_close": round(pre_close, 2),
                "volume": int(volume),
                "amount": round(amount_yuan, 2),
                "turnover": turnover,
                "pe": pe,
                "market_cap": market_cap,
                "circulating_cap": circ_cap,
                "market": "A股" if market == "a" else ("港股" if market == "hk" else "美股"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "_source": "tencent_finance",
            }
            return result

        except Exception:
            return None

    @staticmethod
    def get_realtime_quote(symbol: str) -> Dict[str, Any]:
        """
        获取实时行情快照

        数据源优先级（v3.0）：
        1. 腾讯财经 API（HTTP，国内最快最稳定）
        2. 新浪财经 API（HTTP，备用）
        3. AKShare（HTTPS，可能有 SSL 问题）
        4. 历史 K 线数据 - 最终兜底

        返回：
            price, change, pct_change, volume, amount, turnover, high, low, open, pre_close
        """
        result = {"symbol": symbol, "error": None}
        all_errors = []

        # ---- 方案1: 腾讯财经 API（HTTP，最快） ----
        tencent_result = RealtimeMarketDataService._fetch_tencent_quote(symbol)
        if tencent_result:
            tencent_result["symbol"] = symbol
            tencent_result["error"] = None
            return tencent_result
        all_errors.append("腾讯财经: 获取失败")

        # ---- 方案2: 新浪财经 API（HTTP，备用） ----
        sina_result = RealtimeMarketDataService._fetch_sina_quote(symbol)
        if sina_result:
            sina_result["symbol"] = symbol
            sina_result["error"] = None
            return sina_result
        all_errors.append("新浪财经: 获取失败")

        # ---- 方案3: AKShare（HTTPS，最后尝试） ----
        try:
            import akshare as ak
            market = RealtimeMarketDataService.detect_market(symbol)

            if market == "a":
                # A 股实时行情
                df = ak.stock_zh_a_spot_em()
                code = symbol
                match = df[df["代码"] == code]
                if match.empty:
                    # 尝试去掉前导0
                    match = df[df["代码"] == code.lstrip("0")]
                if match.empty:
                    all_errors.append(f"AKShare A股: 未找到 {symbol}")
                else:
                    row = match.iloc[0]
                    result.update({
                        "name": row.get("名称", ""),
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "pct_change": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                        "turnover": float(row.get("换手率", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "open": float(row.get("开盘", 0)),
                        "pre_close": float(row.get("昨收", 0)),
                        "pe": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
                        "market_cap": float(row.get("总市值", 0)),
                        "circulating_cap": float(row.get("流通市值", 0)),
                        "market": "A股",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "_source": "akshare",
                    })
                    return result

            elif market == "hk":
                # 港股实时行情
                df = ak.stock_hk_spot_em()
                code = symbol.replace(".HK", "")
                match = df[df["代码"] == code]
                if match.empty:
                    all_errors.append(f"AKShare 港股: 未找到 {symbol}")
                else:
                    row = match.iloc[0]
                    result.update({
                        "name": row.get("名称", ""),
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "pct_change": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                        "turnover": float(row.get("换手率", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "open": float(row.get("开盘", 0)),
                        "pre_close": float(row.get("昨收", 0)),
                        "market_cap": float(row.get("总市值", 0)),
                        "market": "港股",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "_source": "akshare",
                    })
                    return result

            elif market == "us":
                # 美股实时行情
                df = ak.stock_us_spot_em()
                match = df[df["代码"] == symbol]
                if match.empty:
                    all_errors.append(f"AKShare 美股: 未找到 {symbol}")
                else:
                    row = match.iloc[0]
                    result.update({
                        "name": row.get("名称", ""),
                        "price": float(row.get("最新价", 0)),
                        "change": float(row.get("涨跌额", 0)),
                        "pct_change": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "amount": float(row.get("成交额", 0)),
                        "turnover": float(row.get("换手率", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "open": float(row.get("开盘", 0)),
                        "pre_close": float(row.get("昨收", 0)),
                        "market_cap": float(row.get("总市值", 0)),
                        "market": "美股",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "_source": "akshare",
                    })
                    return result

        except Exception as e:
            all_errors.append(f"AKShare: {str(e)}")

        # ---- 所有方案都失败 ----
        result["error"] = " | ".join(all_errors)
        return result

    @staticmethod
    def get_fund_flow(symbol: str) -> Dict[str, Any]:
        """
        获取个股资金流向数据（近5日）

        返回：
            主力净流入、超大单净流入、大单净流入、中单净流入、小单净流入
        """
        result = {"symbol": symbol, "error": None}
        try:
            import akshare as ak
            market = RealtimeMarketDataService.detect_market(symbol)

            if market == "a":
                # 判断是沪市还是深市
                s = symbol.strip()
                if s.startswith("6") or s.startswith("9"):
                    market_code = "sh"
                else:
                    market_code = "sz"

                df = ak.stock_individual_fund_flow(stock=s, market=market_code)
                if df is None or df.empty:
                    result["error"] = "无资金流向数据"
                    return result

                # 取最近5日
                df = df.head(5)
                latest = df.iloc[0] if len(df) > 0 else None

                if latest is not None:
                    cols = list(df.columns)
                    result.update({
                        "date": str(latest.iloc[0]) if len(latest) > 0 else "",
                        "close_price": float(latest.iloc[1]) if len(latest) > 1 else 0,
                        "pct_change": float(latest.iloc[2]) if len(latest) > 2 else 0,
                        "main_net_inflow": float(latest.iloc[3]) if len(latest) > 3 else 0,
                        "main_net_inflow_pct": float(latest.iloc[4]) if len(latest) > 4 else 0,
                        "super_large_net_inflow": float(latest.iloc[5]) if len(latest) > 5 else 0,
                        "super_large_net_inflow_pct": float(latest.iloc[6]) if len(latest) > 6 else 0,
                        "large_net_inflow": float(latest.iloc[7]) if len(latest) > 7 else 0,
                        "large_net_inflow_pct": float(latest.iloc[8]) if len(latest) > 8 else 0,
                        "medium_net_inflow": float(latest.iloc[9]) if len(latest) > 9 else 0,
                        "medium_net_inflow_pct": float(latest.iloc[10]) if len(latest) > 10 else 0,
                        "small_net_inflow": float(latest.iloc[11]) if len(latest) > 11 else 0,
                        "small_net_inflow_pct": float(latest.iloc[12]) if len(latest) > 12 else 0,
                    })

                    # 计算5日累计
                    result["5d_main_net_inflow"] = float(df.iloc[:, 3].sum()) if len(df) > 0 else 0
                    result["5d_super_large_net_inflow"] = float(df.iloc[:, 5].sum()) if len(df) > 0 else 0

            else:
                result["error"] = f"{market.upper()} 市场暂不支持个股资金流向查询"

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def get_margin_data(symbol: str) -> Dict[str, Any]:
        """
        获取融资融券数据（仅 A 股）
        """
        result = {"symbol": symbol, "error": None}
        try:
            import akshare as ak
            market = RealtimeMarketDataService.detect_market(symbol)
            if market != "a":
                result["error"] = "仅 A 股支持融资融券查询"
                return result

            # 获取个股融资融券明细
            df = ak.stock_margin_detail_sse()
            if df is not None and not df.empty:
                code = symbol
                match = df[df["证券代码"] == code]
                if not match.empty:
                    row = match.iloc[0]
                    result.update({
                        "margin_balance": float(row.get("融资余额", 0)),
                        "margin_buy": float(row.get("融资买入额", 0)),
                        "margin_repay": float(row.get("融资偿还额", 0)),
                        "short_balance": float(row.get("融券余额", 0)),
                        "short_sell": float(row.get("融券卖出量", 0)),
                        "short_repay": float(row.get("融券偿还量", 0)),
                    })

            # 深市
            df_sz = ak.stock_margin_detail_szse()
            if df_sz is not None and not df_sz.empty and "error" in result:
                code = symbol
                match = df_sz[df_sz["证券代码"] == code]
                if not match.empty:
                    row = match.iloc[0]
                    result.update({
                        "margin_balance": float(row.get("融资余额", 0)),
                        "margin_buy": float(row.get("融资买入额", 0)),
                        "short_balance": float(row.get("融券余额", 0)),
                    })
                    result.pop("error", None)

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def get_north_south_flow() -> Dict[str, Any]:
        """
        获取沪深港通资金流向（北向/南向）
        """
        result = {}
        try:
            import akshare as ak
            df = ak.stock_hsgt_fund_flow_summary_em()
            if df is not None and not df.empty:
                latest = df.iloc[0]
                result.update({
                    "north_money": float(latest.get("沪股通资金净流入", 0)) + float(latest.get("深股通资金净流入", 0)),
                    "sh_north_flow": float(latest.get("沪股通资金净流入", 0)),
                    "sz_north_flow": float(latest.get("深股通资金净流入", 0)),
                    "south_money": float(latest.get("港股通资金净流入", 0)),
                    "date": str(latest.get("日期", "")),
                })
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def get_hot_rank() -> List[Dict[str, Any]]:
        """
        获取市场热度排名（A 股）
        """
        result = []
        try:
            import akshare as ak
            df = ak.stock_hot_rank_em()
            if df is not None and not df.empty:
                for _, row in df.head(10).iterrows():
                    result.append({
                        "rank": int(row.get("序号", 0)),
                        "code": str(row.get("代码", "")),
                        "name": str(row.get("名称", "")),
                        "hot_score": float(row.get("热度", 0)),
                        "pct_change": float(row.get("最新涨跌幅", 0)),
                    })
        except Exception:
            pass
        return result

    @staticmethod
    def get_stock_news(symbol: str) -> List[Dict[str, str]]:
        """
        获取个股相关新闻
        """
        result = []
        try:
            import akshare as ak
            market = RealtimeMarketDataService.detect_market(symbol)
            if market == "a":
                df = ak.stock_news_em(symbol=symbol)
                if df is not None and not df.empty:
                    for _, row in df.head(5).iterrows():
                        result.append({
                            "title": str(row.get("新闻标题", "")),
                            "time": str(row.get("发布时间", "")),
                            "url": str(row.get("新闻链接", "")),
                        })
        except Exception:
            pass
        return result

    @staticmethod
    def get_technical_summary(symbol: str) -> Dict[str, Any]:
        """
        获取技术指标汇总（基于真实行情数据）
        """
        result = {"symbol": symbol, "error": None}
        try:
            service = MarketDataService()
            df = service.get_stock_history(symbol=symbol, period="1y")
            if df is None or df.empty:
                result["error"] = "无法获取历史行情数据"
                return result

            # 计算所有技术指标
            indicators = TechnicalIndicators.calc_all_indicators(df)
            latest = TechnicalIndicators.get_latest_indicators(indicators)
            signal = TechnicalIndicators.get_market_signal(indicators)

            result.update({
                "latest_price": float(df["close"].iloc[-1]) if len(df) > 0 else 0,
                "ma5": float(df["close"].rolling(5).mean().iloc[-1]) if len(df) >= 5 else None,
                "ma10": float(df["close"].rolling(10).mean().iloc[-1]) if len(df) >= 10 else None,
                "ma20": float(df["close"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None,
                "ma60": float(df["close"].rolling(60).mean().iloc[-1]) if len(df) >= 60 else None,
                "ma120": float(df["close"].rolling(120).mean().iloc[-1]) if len(df) >= 120 else None,
                "volume_ma5": float(df["volume"].rolling(5).mean().iloc[-1]) if len(df) >= 5 else None,
                "volume_ma20": float(df["volume"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None,
                "latest_volume": float(df["volume"].iloc[-1]) if len(df) > 0 else 0,
                "high_52w": float(df["high"].max()) if len(df) > 0 else 0,
                "low_52w": float(df["low"].min()) if len(df) > 0 else 0,
                "pct_change_1d": float(df["close"].pct_change().iloc[-1] * 100) if len(df) > 1 else 0,
                "pct_change_5d": float((df["close"].iloc[-1] / df["close"].iloc[-5] - 1) * 100) if len(df) >= 5 else 0,
                "pct_change_20d": float((df["close"].iloc[-1] / df["close"].iloc[-20] - 1) * 100) if len(df) >= 20 else 0,
                "volatility_20d": float(df["close"].pct_change().rolling(20).std().iloc[-1] * 100) if len(df) >= 20 else 0,
                "signal": signal,
                "indicators": latest,
            })

            # 判断均线排列状态
            if all(v is not None for v in [result["ma5"], result["ma10"], result["ma20"], result["ma60"]]):
                if result["ma5"] > result["ma10"] > result["ma20"] > result["ma60"]:
                    result["ma_status"] = "多头排列"
                elif result["ma5"] < result["ma10"] < result["ma20"] < result["ma60"]:
                    result["ma_status"] = "空头排列"
                else:
                    result["ma_status"] = "缠绕震荡"
            else:
                result["ma_status"] = "数据不足"

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def get_sector_fund_flow() -> Dict[str, Any]:
        """
        获取板块资金流向排名
        """
        result = {"leading_sectors": [], "lagging_sectors": []}
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                for _, row in df.head(5).iterrows():
                    result["leading_sectors"].append({
                        "name": str(row.get("板块名称", "")),
                        "flow": float(row.get("主力净流入-净额", 0)),
                        "pct_change": float(row.get("涨跌幅", 0)),
                    })
                for _, row in df.tail(5).iterrows():
                    result["lagging_sectors"].append({
                        "name": str(row.get("板块名称", "")),
                        "flow": float(row.get("主力净流入-净额", 0)),
                        "pct_change": float(row.get("涨跌幅", 0)),
                    })
        except Exception:
            pass
        return result

    @classmethod
    def get_comprehensive_market_data(cls, symbol: str) -> Dict[str, Any]:
        """
        获取综合市场数据（聚合所有维度）- 并行化 + 缓存优化版

        使用 ThreadPoolExecutor 并发请求所有接口，大幅降低等待时间。
        对不频繁变化的数据使用内存缓存（5分钟有效期）。
        """
        data = {
            "symbol": symbol,
            "market": cls.detect_market(symbol),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        def _fetch_quote():
            cache_key = f"quote_{symbol}"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("quote", cached)
            result = cls.get_realtime_quote(symbol)
            if result and not result.get("error"):
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["quote"])
                return ("quote", result)
            return ("quote", None)

        def _fetch_technical():
            cache_key = f"technical_{symbol}"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("technical", cached)
            result = cls.get_technical_summary(symbol)
            if result and not result.get("error"):
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["technical"])
                return ("technical", result)
            return ("technical", None)

        def _fetch_fund_flow():
            cache_key = f"fund_flow_{symbol}"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("fund_flow", cached)
            result = cls.get_fund_flow(symbol)
            if result and not result.get("error"):
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["fund_flow"])
                return ("fund_flow", result)
            return ("fund_flow", None)

        def _fetch_margin():
            cache_key = f"margin_{symbol}"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("margin", cached)
            result = cls.get_margin_data(symbol)
            if result and not result.get("error"):
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["margin"])
                return ("margin", result)
            return ("margin", None)

        def _fetch_north_south():
            cache_key = "north_south"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("north_south_flow", cached)
            result = cls.get_north_south_flow()
            if result and not result.get("error"):
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["north_south"])
                return ("north_south_flow", result)
            return ("north_south_flow", None)

        def _fetch_sector():
            cache_key = "sector_flow"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("sector_flow", cached)
            result = cls.get_sector_fund_flow()
            if result:
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["sector"])
                return ("sector_flow", result)
            return ("sector_flow", None)

        def _fetch_hot_rank():
            cache_key = "hot_rank"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("hot_rank", cached)
            result = cls.get_hot_rank()
            if result:
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["hot_rank"])
                return ("hot_rank", result)
            return ("hot_rank", None)

        def _fetch_news():
            cache_key = f"news_{symbol}"
            cached = cls._get_cache(cache_key)
            if cached:
                return ("news", cached)
            result = cls.get_stock_news(symbol)
            if result:
                cls._set_cache(cache_key, result, cls._CACHE_DURATION["news"])
                return ("news", result)
            return ("news", None)

        # 并行执行所有数据获取任务
        tasks = [
            _fetch_quote, _fetch_technical, _fetch_fund_flow,
            _fetch_margin, _fetch_north_south, _fetch_sector,
            _fetch_hot_rank, _fetch_news,
        ]

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_name = {executor.submit(task): task for task in tasks}
            for future in as_completed(future_to_name, timeout=30):
                try:
                    key, value = future.result(timeout=10)
                    if value is not None:
                        data[key] = value
                except Exception:
                    pass  # 单个接口失败不影响整体

        return data

    @staticmethod
    def format_market_data_for_prompt(market_data: Dict[str, Any]) -> str:
        """
        将市场数据格式化为 AI Prompt 可读的文本

        这是核心方法：将真实数据转换成结构化的文本描述，
        供 LLM 在分析时使用。

        【重要】AI 必须严格基于以下提供的真实数据进行分析，
        不得编造或虚构任何价格数据。如果数据缺失，请明确标注"数据不可用"。
        """
        lines = []
        is_fallback = market_data.get("_fallback", False)
        quote_source = market_data.get("quote", {}).get("_source", "unknown")

        # ---- 数据来源声明 ----
        if is_fallback:
            lines.append("【⚠️ 重要提示：以下数据来自历史K线数据，非实时行情】")
            lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
            lines.append("说明：当前实时行情接口不可用，以下价格数据基于最近交易日的历史K线收盘价。")
            lines.append("涨跌幅、换手率等数据为历史数据，仅供参考，不代表当前实时交易情况。")
        elif quote_source == "tencent_finance":
            lines.append("【实时市场数据 - 来源：腾讯财经】")
            lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
            lines.append("说明：以下数据通过腾讯财经 API 获取，为实时行情数据，包含换手率、市盈率、市值等。")
        elif quote_source == "sina_finance":
            lines.append("【实时市场数据 - 来源：新浪财经】")
            lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
            lines.append("说明：以下数据通过新浪财经 API 获取，为实时行情数据。")
        elif quote_source == "akshare":
            lines.append("【实时市场数据 - 来源：AKShare（东方财富接口）】")
            lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
            lines.append("说明：以下数据通过 AKShare 获取，为实时行情数据。")
        else:
            lines.append("【实时市场数据 - 来源：历史K线数据】")
            lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
            lines.append("说明：以下数据基于最近交易日的历史K线收盘价，非实时行情。")
        lines.append("")

        # ---- 重要：AI 不得编造数据的声明 ----
        lines.append("【\u26a0\ufe0f AI 必须遵守的规则】")
        lines.append("1. 以下所有价格、涨跌幅、成交量等数据均为真实获取的数据，AI 必须严格基于这些数据进行分析。")
        lines.append('2. AI 不得编造、虚构或\u201c合理推断\u201d任何价格数据。如果某个字段显示为 N/A 或数据不可用，')
        lines.append('   请在分析报告中明确标注\u201c数据不可用\u201d，不得自行编造数值。')
        lines.append('3. 如果数据来源标记为历史K线数据，AI 必须在报告中注明\u201c基于历史数据，非实时行情\u201d。')
        lines.append("")

        # 1. 实时行情
        quote = market_data.get("quote", {})
        if quote:
            lines.append("═══ 实时行情快照 ═══")
            lines.append(f"股票名称: {quote.get('name', 'N/A')}")
            lines.append(f"最新价: {quote.get('price', 'N/A')}")
            lines.append(f"涨跌额: {quote.get('change', 'N/A')}")
            lines.append(f"涨跌幅: {quote.get('pct_change', 'N/A')}%")
            lines.append(f"今开: {quote.get('open', 'N/A')}  最高: {quote.get('high', 'N/A')}  最低: {quote.get('low', 'N/A')}")
            lines.append(f"昨收: {quote.get('pre_close', 'N/A')}")
            lines.append(f"成交量: {quote.get('volume', 'N/A')}")
            lines.append(f"成交额: {quote.get('amount', 'N/A')}")
            lines.append(f"换手率: {quote.get('turnover', 'N/A')}%")
            if quote.get('pe'):
                lines.append(f"动态市盈率: {quote.get('pe')}")
            if quote.get('market_cap'):
                lines.append(f"总市值: {quote.get('market_cap')}")
            if quote.get('circulating_cap'):
                lines.append(f"流通市值: {quote.get('circulating_cap')}")
            lines.append("")

        # 2. 技术指标
        tech = market_data.get("technical", {})
        if tech:
            lines.append("═══ 技术指标汇总（基于真实行情数据计算） ═══")
            lines.append(f"当前价格: {tech.get('latest_price', 'N/A')}")
            lines.append(f"均线系统: MA5={tech.get('ma5', 'N/A')}  MA10={tech.get('ma10', 'N/A')}  MA20={tech.get('ma20', 'N/A')}  MA60={tech.get('ma60', 'N/A')}")
            lines.append(f"均线排列状态: {tech.get('ma_status', 'N/A')}")
            lines.append(f"52周最高: {tech.get('high_52w', 'N/A')}  52周最低: {tech.get('low_52w', 'N/A')}")
            lines.append(f"近1日涨跌: {tech.get('pct_change_1d', 'N/A')}%  近5日涨跌: {tech.get('pct_change_5d', 'N/A')}%  近20日涨跌: {tech.get('pct_change_20d', 'N/A')}%")
            lines.append(f"20日波动率: {tech.get('volatility_20d', 'N/A')}%")
            lines.append(f"最新成交量: {tech.get('latest_volume', 'N/A')}  (5日均量: {tech.get('volume_ma5', 'N/A')}  20日均量: {tech.get('volume_ma20', 'N/A')})")

            indicators = tech.get("indicators", {})
            if indicators:
                macd = indicators.get("macd", {})
                if macd:
                    lines.append(f"MACD: DIF={macd.get('dif', 'N/A')}  DEA={macd.get('dea', 'N/A')}  MACD柱={macd.get('macd', 'N/A')}  状态={macd.get('status', 'N/A')}")
                kdj = indicators.get("kdj", {})
                if kdj:
                    lines.append(f"KDJ: K={kdj.get('k', 'N/A')}  D={kdj.get('d', 'N/A')}  J={kdj.get('j', 'N/A')}  状态={kdj.get('status', 'N/A')}")
                rsi = indicators.get("rsi", {})
                if rsi:
                    lines.append(f"RSI(14): {rsi.get('rsi', 'N/A')}  状态={rsi.get('status', 'N/A')}")
                boll = indicators.get("bollinger", {})
                if boll:
                    lines.append(f"布林带: 上轨={boll.get('upper', 'N/A')}  中轨={boll.get('mid', 'N/A')}  下轨={boll.get('lower', 'N/A')}  带宽={boll.get('bandwidth', 'N/A')}%  位置={boll.get('position', 'N/A')}")

            signal = tech.get("signal", {})
            if signal:
                lines.append(f"综合信号: {signal.get('signal', 'N/A')} (置信度: {signal.get('confidence', 'N/A')})")
            lines.append("")

        # 3. 资金流向
        fund = market_data.get("fund_flow", {})
        if fund:
            lines.append("═══ 资金流向数据（最新交易日） ═══")
            lines.append(f"主力净流入: {fund.get('main_net_inflow', 'N/A')} (占比: {fund.get('main_net_inflow_pct', 'N/A')}%)")
            lines.append(f"超大单净流入: {fund.get('super_large_net_inflow', 'N/A')} (占比: {fund.get('super_large_net_inflow_pct', 'N/A')}%)")
            lines.append(f"大单净流入: {fund.get('large_net_inflow', 'N/A')} (占比: {fund.get('large_net_inflow_pct', 'N/A')}%)")
            lines.append(f"中单净流入: {fund.get('medium_net_inflow', 'N/A')} (占比: {fund.get('medium_net_inflow_pct', 'N/A')}%)")
            lines.append(f"小单净流入: {fund.get('small_net_inflow', 'N/A')} (占比: {fund.get('small_net_inflow_pct', 'N/A')}%)")
            if fund.get('5d_main_net_inflow'):
                lines.append(f"5日主力累计净流入: {fund.get('5d_main_net_inflow', 'N/A')}")
            lines.append("")

        # 4. 融资融券
        margin = market_data.get("margin", {})
        if margin:
            lines.append("═══ 融资融券数据 ═══")
            lines.append(f"融资余额: {margin.get('margin_balance', 'N/A')}")
            lines.append(f"融资买入额: {margin.get('margin_buy', 'N/A')}")
            lines.append(f"融券余额: {margin.get('short_balance', 'N/A')}")
            lines.append("")

        # 5. 沪深港通
        hsgt = market_data.get("north_south_flow", {})
        if hsgt:
            lines.append("═══ 沪深港通资金流向 ═══")
            lines.append(f"北向资金净流入: {hsgt.get('north_money', 'N/A')} (沪股通: {hsgt.get('sh_north_flow', 'N/A')}  深股通: {hsgt.get('sz_north_flow', 'N/A')})")
            lines.append(f"南向资金净流入: {hsgt.get('south_money', 'N/A')}")
            lines.append("")

        # 6. 板块资金流向
        sector = market_data.get("sector_flow", {})
        if sector:
            lines.append("═══ 板块资金流向排名 ═══")
            leading = sector.get("leading_sectors", [])
            if leading:
                lines.append("【主力净流入前5板块】")
                for s in leading:
                    lines.append(f"  {s.get('name', '')}: 净流入{s.get('flow', 0)}  涨跌幅{s.get('pct_change', 0)}%")
            lagging = sector.get("lagging_sectors", [])
            if lagging:
                lines.append("【主力净流出前5板块】")
                for s in lagging:
                    lines.append(f"  {s.get('name', '')}: 净流出{abs(s.get('flow', 0))}  涨跌幅{s.get('pct_change', 0)}%")
            lines.append("")

        # 7. 热度排名
        hot = market_data.get("hot_rank", [])
        if hot:
            lines.append("═══ 市场热度排名 Top10 ═══")
            for h in hot[:5]:
                lines.append(f"  #{h.get('rank', '')} {h.get('name', '')}({h.get('code', '')}) 热度:{h.get('hot_score', '')} 涨跌幅:{h.get('pct_change', '')}%")
            lines.append("")

        # 8. 个股新闻
        news = market_data.get("news", [])
        if news:
            lines.append("═══ 个股相关新闻 ═══")
            for n in news[:3]:
                lines.append(f"  [{n.get('time', '')}] {n.get('title', '')}")
            lines.append("")

        # ---- 数据来源脚注 ----
        if is_fallback:
            lines.append("【数据来源】历史K线数据（AKShare）| 非实时行情，仅供技术分析参考")
        elif quote_source == "tencent_finance":
            lines.append("【数据来源】腾讯财经 API 实时行情 | 数据仅供分析参考，不构成投资建议")
        elif quote_source == "sina_finance":
            lines.append("【数据来源】新浪财经 API 实时行情 | 数据仅供分析参考，不构成投资建议")
        elif quote_source == "akshare":
            lines.append("【数据来源】AKShare（东方财富接口）实时行情 | 数据仅供分析参考，不构成投资建议")
        else:
            lines.append("【数据来源】历史K线数据 | 非实时行情，仅供技术分析参考")
        lines.append("")

        # ---- 始终附加历史K线摘要（防止AI数据不足时编造） ----
        history_summary = market_data.get("_history_summary", "")
        if history_summary:
            lines.append("")
            lines.append("═══ 历史K线数据摘要（备用参考） ═══")
            lines.append(history_summary)
            lines.append("【说明】以上历史K线数据为备用参考数据，AI 在分析实时行情数据不足时可以使用这些数据，")
            lines.append("但必须在报告中明确标注使用的是历史数据而非实时行情。")
            lines.append("")

        return "\n".join(lines)
