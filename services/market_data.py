"""
行情数据服务模块
================
封装 AKShare 接口，提供 A 股/港股/美股历史行情数据获取。
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class MarketDataService:
    """行情数据服务，支持 A 股、港股、美股"""

    @staticmethod
    def get_stock_history(
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史行情数据

        Args:
            symbol: 股票代码（如 600519、0700.HK、AAPL）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 时间范围（1m, 3m, 6m, 1y, 2y, 5y）

        Returns:
            DataFrame 包含 OHLCV 数据，失败返回 None
        """
        symbol = symbol.strip().upper()

        # 自动判断市场并设置日期
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            period_map = {
                "1m": 30, "3m": 90, "6m": 180,
                "1y": 365, "2y": 730, "5y": 1825,
            }
            days = period_map.get(period, 365)
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        try:
            if symbol.endswith(".HK"):
                # 港股
                return MarketDataService._get_hk_stock(symbol, start_date, end_date)
            elif symbol in ("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "BABA", "JD", "BIDU"):
                # 美股 - 使用 yfinance 替代方案
                return MarketDataService._get_us_stock(symbol, start_date, end_date)
            else:
                # A 股
                return MarketDataService._get_a_stock(symbol, start_date, end_date)
        except Exception as e:
            print(f"获取行情数据失败 [{symbol}]: {e}")
            return None

    @staticmethod
    def _get_a_stock(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取 A 股历史行情"""
        try:
            import akshare as ak

            # 添加市场后缀
            if symbol.startswith("6") or symbol.startswith("9"):
                a_symbol = f"{symbol}"
            elif symbol.startswith("0") or symbol.startswith("3"):
                a_symbol = f"{symbol}"
            else:
                a_symbol = symbol

            df = ak.stock_zh_a_hist(
                symbol=a_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # 前复权
            )
            if df is None or df.empty:
                return None

            # 标准化列名
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "振幅": "amplitude",
                "涨跌幅": "pct_change", "涨跌额": "change",
                "换手率": "turnover",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            return df

        except ImportError:
            print("请安装 akshare: pip install akshare")
            return None
        except Exception as e:
            print(f"A 股数据获取失败: {e}")
            return None

    @staticmethod
    def _get_hk_stock(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取港股历史行情"""
        try:
            import akshare as ak

            code = symbol.replace(".HK", "")
            df = ak.stock_hk_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df is None or df.empty:
                return None

            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "涨跌幅": "pct_change",
                "涨跌额": "change", "换手率": "turnover",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            return df

        except Exception as e:
            print(f"港股数据获取失败: {e}")
            return None

    @staticmethod
    def _get_us_stock(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取美股历史行情（通过 AKShare 的美股接口）"""
        try:
            import akshare as ak

            df = ak.stock_us_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df is None or df.empty:
                return None

            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "涨跌幅": "pct_change",
                "涨跌额": "change", "换手率": "turnover",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            return df

        except Exception as e:
            print(f"美股数据获取失败: {e}")
            return None

    @staticmethod
    def plot_candlestick(df: pd.DataFrame, symbol: str, title: str = "") -> go.Figure:
        """
        绘制交互式 K 线图

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            symbol: 股票代码
            title: 图表标题

        Returns:
            plotly Figure 对象
        """
        # 计算移动平均线
        df["ma5"] = df["close"].rolling(window=5).mean()
        df["ma10"] = df["close"].rolling(window=10).mean()
        df["ma20"] = df["close"].rolling(window=20).mean()
        df["ma60"] = df["close"].rolling(window=60).mean()

        # 计算成交量颜色
        df["volume_color"] = df.apply(
            lambda row: "#00D4AA" if row["close"] >= row["open"] else "#FF4D4D",
            axis=1,
        )

        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
        )

        # K 线图
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K线",
                increasing_line_color="#00D4AA",
                decreasing_line_color="#FF4D4D",
            ),
            row=1, col=1,
        )

        # 移动平均线
        for ma, color, name in [
            ("ma5", "#FFC107", "MA5"),
            ("ma10", "#00A3FF", "MA10"),
            ("ma20", "#FF9800", "MA20"),
            ("ma60", "#E040FB", "MA60"),
        ]:
            if ma in df.columns and df[ma].notna().sum() > 0:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df[ma],
                        mode="lines",
                        line=dict(color=color, width=1),
                        name=name,
                    ),
                    row=1, col=1,
                )

        # 成交量柱状图
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color=df["volume_color"],
                opacity=0.8,
            ),
            row=2, col=1,
        )

        # 布局设置
        title_text = f"{symbol} K线图" if not title else title
        fig.update_layout(
            title=dict(
                text=title_text,
                font=dict(size=20, color="#00D4AA"),
                x=0.5,
            ),
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#1A1D27",
            xaxis_rangeslider_visible=False,
            height=700,
            margin=dict(l=50, r=50, t=80, b=50),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10, color="#8892B0"),
            ),
        )

        # 坐标轴样式
        fig.update_xaxes(
            gridcolor="#2A2D3E",
            zerolinecolor="#2A2D3E",
            tickfont=dict(color="#8892B0"),
            row=1, col=1,
        )
        fig.update_xaxes(
            gridcolor="#2A2D3E",
            zerolinecolor="#2A2D3E",
            tickfont=dict(color="#8892B0"),
            row=2, col=1,
        )
        fig.update_yaxes(
            gridcolor="#2A2D3E",
            zerolinecolor="#2A2D3E",
            tickfont=dict(color="#8892B0"),
            row=1, col=1,
        )
        fig.update_yaxes(
            gridcolor="#2A2D3E",
            zerolinecolor="#2A2D3E",
            tickfont=dict(color="#8892B0"),
            row=2, col=1,
        )

        return fig

    @staticmethod
    def get_stock_info(symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            股票基本信息字典
        """
        try:
            import akshare as ak

            symbol = symbol.strip().upper()

            if symbol.endswith(".HK"):
                code = symbol.replace(".HK", "")
                df = ak.stock_hk_spot()
                if df is not None and not df.empty:
                    row = df[df["代码"] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": r.get("名称", ""),
                            "code": symbol,
                            "price": r.get("最新价", ""),
                            "change": r.get("涨跌幅", ""),
                            "volume": r.get("成交量", ""),
                            "amount": r.get("成交额", ""),
                            "market": "港股",
                        }
            elif symbol in ("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"):
                df = ak.stock_us_spot()
                if df is not None and not df.empty:
                    row = df[df["代码"] == symbol]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": r.get("名称", ""),
                            "code": symbol,
                            "price": r.get("最新价", ""),
                            "change": r.get("涨跌幅", ""),
                            "volume": r.get("成交量", ""),
                            "amount": r.get("成交额", ""),
                            "market": "美股",
                        }
            else:
                # A 股
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    row = df[df["代码"] == symbol]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": r.get("名称", ""),
                            "code": symbol,
                            "price": r.get("最新价", ""),
                            "change": r.get("涨跌幅", ""),
                            "volume": r.get("成交量", ""),
                            "amount": r.get("成交额", ""),
                            "market": "A股",
                        }

            return {"name": "", "code": symbol, "error": "未找到该股票信息"}

        except Exception as e:
            return {"name": "", "code": symbol, "error": str(e)}
