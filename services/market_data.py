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
    def plot_candlestick(df: pd.DataFrame, symbol: str, title: str = "",
                         show_indicators: bool = True) -> go.Figure:
        """
        绘制交互式 K 线图（增强版，含技术指标子图）

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            symbol: 股票代码
            title: 图表标题
            show_indicators: 是否显示技术指标子图（MACD/RSI/KDJ）

        Returns:
            plotly Figure 对象
        """
        # 复制数据避免修改原始数据
        df = df.copy()

        # 计算移动平均线
        df["ma5"] = df["close"].rolling(window=5).mean()
        df["ma10"] = df["close"].rolling(window=10).mean()
        df["ma20"] = df["close"].rolling(window=20).mean()
        df["ma60"] = df["close"].rolling(window=60).mean()

        # 计算布林带
        df["boll_mid"] = df["close"].rolling(window=20).mean()
        df["boll_std"] = df["close"].rolling(window=20).std()
        df["boll_upper"] = df["boll_mid"] + 2 * df["boll_std"]
        df["boll_lower"] = df["boll_mid"] - 2 * df["boll_std"]

        # 计算 MACD
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd_dif"] = ema12 - ema26
        df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = 2 * (df["macd_dif"] - df["macd_dea"])

        # 计算 RSI(14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # 计算 KDJ(9,3,3)
        low_9 = df["low"].rolling(window=9).min()
        high_9 = df["high"].rolling(window=9).max()
        rsv = (df["close"] - low_9) / (high_9 - low_9) * 100
        df["kdj_k"] = rsv.ewm(com=2, adjust=False).mean()
        df["kdj_d"] = df["kdj_k"].ewm(com=2, adjust=False).mean()
        df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]

        # 计算成交量颜色
        df["volume_color"] = df.apply(
            lambda row: "#00D4AA" if row["close"] >= row["open"] else "#FF4D4D",
            axis=1,
        )

        # 计算成交量 MA
        df["volume_ma5"] = df["volume"].rolling(window=5).mean()
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()

        # 确定子图数量
        if show_indicators:
            # 4行: K线+布林带 | 成交量 | MACD | RSI+KDJ
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[0.45, 0.18, 0.18, 0.19],
                subplot_titles=("价格走势", "成交量", "MACD", "RSI / KDJ"),
            )
        else:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
            )

        # ========== 主图：K线 + 均线 + 布林带 ==========
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
                showlegend=True,
            ),
            row=1, col=1,
        )

        # 移动平均线
        for ma, color, name, width in [
            ("ma5", "#FFC107", "MA5", 1.2),
            ("ma10", "#00A3FF", "MA10", 1.2),
            ("ma20", "#FF9800", "MA20", 1.2),
            ("ma60", "#E040FB", "MA60", 1),
        ]:
            if ma in df.columns and df[ma].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df[ma],
                        mode="lines",
                        line=dict(color=color, width=width),
                        name=name,
                    ),
                    row=1, col=1,
                )

        # 布林带
        if "boll_upper" in df.columns and df["boll_upper"].notna().sum() > 5:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["boll_upper"],
                    mode="lines",
                    line=dict(color="rgba(0, 163, 255, 0.3)", width=0.8),
                    name="布林上轨",
                    showlegend=True,
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["boll_lower"],
                    mode="lines",
                    line=dict(color="rgba(0, 163, 255, 0.3)", width=0.8),
                    name="布林下轨",
                    fill="tonexty",
                    fillcolor="rgba(0, 163, 255, 0.05)",
                    showlegend=True,
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["boll_mid"],
                    mode="lines",
                    line=dict(color="rgba(0, 163, 255, 0.2)", width=0.5, dash="dash"),
                    name="布林中轨",
                    showlegend=True,
                ),
                row=1, col=1,
            )

        # ========== 成交量图 ==========
        vol_row = 2
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color=df["volume_color"],
                opacity=0.7,
            ),
            row=vol_row, col=1,
        )

        # 成交量均线
        if "volume_ma5" in df.columns and df["volume_ma5"].notna().sum() > 5:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["volume_ma5"],
                    mode="lines",
                    line=dict(color="#FFC107", width=1),
                    name="量MA5",
                ),
                row=vol_row, col=1,
            )
        if "volume_ma20" in df.columns and df["volume_ma20"].notna().sum() > 5:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["volume_ma20"],
                    mode="lines",
                    line=dict(color="#FF9800", width=1),
                    name="量MA20",
                ),
                row=vol_row, col=1,
            )

        if show_indicators:
            # ========== MACD 子图 (row 3) ==========
            macd_row = 3
            # MACD 柱状体
            macd_colors = df["macd_hist"].apply(
                lambda x: "#00D4AA" if x >= 0 else "#FF4D4D"
            )
            fig.add_trace(
                go.Bar(
                    x=df["date"],
                    y=df["macd_hist"],
                    name="MACD柱",
                    marker_color=macd_colors,
                    opacity=0.6,
                ),
                row=macd_row, col=1,
            )
            # DIF 线
            if df["macd_dif"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["macd_dif"],
                        mode="lines",
                        line=dict(color="#00A3FF", width=1.5),
                        name="DIF",
                    ),
                    row=macd_row, col=1,
                )
            # DEA 线
            if df["macd_dea"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["macd_dea"],
                        mode="lines",
                        line=dict(color="#FFC107", width=1.5),
                        name="DEA",
                    ),
                    row=macd_row, col=1,
                )
            # 零轴线
            fig.add_hline(
                y=0, line=dict(color="rgba(255,255,255,0.2)", width=0.5),
                row=macd_row, col=1,
            )

            # ========== RSI + KDJ 子图 (row 4) ==========
            rsi_row = 4

            # RSI 线
            if df["rsi_14"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["rsi_14"],
                        mode="lines",
                        line=dict(color="#E040FB", width=1.5),
                        name="RSI(14)",
                    ),
                    row=rsi_row, col=1,
                )

            # KDJ 线
            if df["kdj_k"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["kdj_k"],
                        mode="lines",
                        line=dict(color="#00D4AA", width=1),
                        name="K",
                    ),
                    row=rsi_row, col=1,
                )
            if df["kdj_d"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["kdj_d"],
                        mode="lines",
                        line=dict(color="#FFC107", width=1),
                        name="D",
                    ),
                    row=rsi_row, col=1,
                )
            if df["kdj_j"].notna().sum() > 5:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["kdj_j"],
                        mode="lines",
                        line=dict(color="#FF9800", width=0.8, dash="dash"),
                        name="J",
                    ),
                    row=rsi_row, col=1,
                )

            # RSI 超买超卖线
            fig.add_hline(
                y=70, line=dict(color="rgba(255, 77, 77, 0.3)", width=0.8, dash="dash"),
                row=rsi_row, col=1,
            )
            fig.add_hline(
                y=30, line=dict(color="rgba(0, 212, 170, 0.3)", width=0.8, dash="dash"),
                row=rsi_row, col=1,
            )

        # ========== 布局设置 ==========
        title_text = f"{symbol} K线图" if not title else title
        fig.update_layout(
            title=dict(
                text=title_text,
                font=dict(size=18, color="#00D4AA"),
                x=0.5,
            ),
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#1A1D27",
            xaxis_rangeslider_visible=False,
            height=900 if show_indicators else 700,
            margin=dict(l=50, r=50, t=80, b=50),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=9, color="#8892B0"),
            ),
        )

        # ========== 坐标轴样式 ==========
        for row_idx in range(1, 5):
            if not show_indicators and row_idx > 2:
                break
            fig.update_xaxes(
                gridcolor="#2A2D3E",
                zerolinecolor="#2A2D3E",
                tickfont=dict(color="#8892B0", size=10),
                row=row_idx, col=1,
            )
            fig.update_yaxes(
                gridcolor="#2A2D3E",
                zerolinecolor="#2A2D3E",
                tickfont=dict(color="#8892B0", size=10),
                row=row_idx, col=1,
            )

        # 隐藏非底部子图的 x 轴标签
        if show_indicators:
            for row_idx in range(1, 4):
                fig.update_xaxes(
                    visible=False,
                    row=row_idx, col=1,
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
