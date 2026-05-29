"""
实时市场数据聚合服务
====================
基于 AKShare 免费接口，聚合多维度实时市场数据。
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
"""

import json
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

    @staticmethod
    def detect_market(symbol: str) -> str:
        """检测股票所属市场"""
        s = symbol.strip().upper()
        if s.endswith(".HK"):
            return "hk"
        if s in RealtimeMarketDataService.US_STOCKS or s.isalpha():
            return "us"
        return "a"

    @staticmethod
    def get_realtime_quote(symbol: str) -> Dict[str, Any]:
        """
        获取实时行情快照

        返回：
            price, change, pct_change, volume, amount, turnover, high, low, open, pre_close
        """
        result = {"symbol": symbol, "error": None}
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
                    result["error"] = f"未找到 {symbol} 的实时行情"
                    return result

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
                })

            elif market == "hk":
                # 港股实时行情
                df = ak.stock_hk_spot_em()
                code = symbol.replace(".HK", "")
                match = df[df["代码"] == code]
                if match.empty:
                    result["error"] = f"未找到 {symbol} 的实时行情"
                    return result
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
                })

            elif market == "us":
                # 美股实时行情
                df = ak.stock_us_spot_em()
                match = df[df["代码"] == symbol]
                if match.empty:
                    result["error"] = f"未找到 {symbol} 的实时行情"
                    return result
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
                })

        except Exception as e:
            result["error"] = str(e)

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

    @staticmethod
    def get_comprehensive_market_data(symbol: str) -> Dict[str, Any]:
        """
        获取综合市场数据（聚合所有维度）

        这是供 AI Prompt 注入使用的核心方法。
        """
        data = {
            "symbol": symbol,
            "market": RealtimeMarketDataService.detect_market(symbol),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 1. 实时行情
        quote = RealtimeMarketDataService.get_realtime_quote(symbol)
        if quote and not quote.get("error"):
            data["quote"] = quote

        # 2. 技术指标汇总
        tech = RealtimeMarketDataService.get_technical_summary(symbol)
        if tech and not tech.get("error"):
            data["technical"] = tech

        # 3. 资金流向
        fund = RealtimeMarketDataService.get_fund_flow(symbol)
        if fund and not fund.get("error"):
            data["fund_flow"] = fund

        # 4. 融资融券（仅 A 股）
        margin = RealtimeMarketDataService.get_margin_data(symbol)
        if margin and not margin.get("error"):
            data["margin"] = margin

        # 5. 沪深港通
        hsgt = RealtimeMarketDataService.get_north_south_flow()
        if hsgt and not hsgt.get("error"):
            data["north_south_flow"] = hsgt

        # 6. 板块资金流向
        sector = RealtimeMarketDataService.get_sector_fund_flow()
        if sector:
            data["sector_flow"] = sector

        # 7. 热度排名
        hot = RealtimeMarketDataService.get_hot_rank()
        if hot:
            data["hot_rank"] = hot

        # 8. 个股新闻
        news = RealtimeMarketDataService.get_stock_news(symbol)
        if news:
            data["news"] = news

        return data

    @staticmethod
    def format_market_data_for_prompt(market_data: Dict[str, Any]) -> str:
        """
        将市场数据格式化为 AI Prompt 可读的文本

        这是核心方法：将真实数据转换成结构化的文本描述，
        供 LLM 在分析时使用。
        """
        lines = []
        lines.append("【实时市场数据 - 仅供 AI 分析参考】")
        lines.append(f"数据时间: {market_data.get('timestamp', 'N/A')}")
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

        lines.append("【数据来源】AKShare 实时行情接口 | 数据仅供分析参考，不构成投资建议")
        lines.append("")

        return "\n".join(lines)
