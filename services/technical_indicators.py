"""
技术指标计算模块
================
基于真实行情数据计算专业级技术分析指标。
支持 MACD、KDJ、RSI、布林带、均线系统、量价关系等。
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple


class TechnicalIndicators:
    """专业级技术指标计算器"""

    @staticmethod
    def calc_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        """
        计算 MACD 指标

        Args:
            df: 包含 close 列的 DataFrame
            fast: 快线周期（默认 12）
            slow: 慢线周期（默认 26）
            signal: 信号线周期（默认 9）

        Returns:
            包含 MACD 指标的 DataFrame
        """
        df = df.copy()
        close = df["close"]
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        df["macd_dif"] = ema_fast - ema_slow
        df["macd_dea"] = df["macd_dif"].ewm(span=signal, adjust=False).mean()
        df["macd_hist"] = 2 * (df["macd_dif"] - df["macd_dea"])
        return df

    @staticmethod
    def calc_kdj(
        df: pd.DataFrame,
        n: int = 9,
        k_period: int = 3,
        d_period: int = 3,
    ) -> pd.DataFrame:
        """
        计算 KDJ 指标

        Args:
            df: 包含 high, low, close 列的 DataFrame
            n: 周期（默认 9）
            k_period: K 值平滑周期（默认 3）
            d_period: D 值平滑周期（默认 3）

        Returns:
            包含 KDJ 指标的 DataFrame
        """
        df = df.copy()
        low_n = df["low"].rolling(window=n).min()
        high_n = df["high"].rolling(window=n).max()

        rsv = (df["close"] - low_n) / (high_n - low_n) * 100

        df["kdj_k"] = rsv.ewm(com=k_period - 1, adjust=False).mean()
        df["kdj_d"] = df["kdj_k"].ewm(com=d_period - 1, adjust=False).mean()
        df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]

        return df

    @staticmethod
    def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算 RSI 指标

        Args:
            df: 包含 close 列的 DataFrame
            period: 周期（默认 14）

        Returns:
            包含 RSI 指标的 DataFrame
        """
        df = df.copy()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        # Wilder 平滑法
        for i in range(period, len(avg_gain)):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df[f"rsi_{period}"] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def calc_bollinger(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> pd.DataFrame:
        """
        计算布林带指标

        Args:
            df: 包含 close 列的 DataFrame
            period: 周期（默认 20）
            std_dev: 标准差倍数（默认 2.0）

        Returns:
            包含布林带指标的 DataFrame
        """
        df = df.copy()
        df["boll_mid"] = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        df["boll_upper"] = df["boll_mid"] + std_dev * std
        df["boll_lower"] = df["boll_mid"] - std_dev * std
        df["boll_width"] = (df["boll_upper"] - df["boll_lower"]) / df["boll_mid"] * 100
        df["boll_position"] = (df["close"] - df["boll_lower"]) / (df["boll_upper"] - df["boll_lower"])
        return df

    @staticmethod
    def calc_ma(df: pd.DataFrame, periods: Optional[list] = None) -> pd.DataFrame:
        """
        计算移动平均线

        Args:
            df: 包含 close 列的 DataFrame
            periods: 均线周期列表，默认 [5, 10, 20, 30, 60, 120, 250]

        Returns:
            包含 MA 指标的 DataFrame
        """
        if periods is None:
            periods = [5, 10, 20, 30, 60, 120, 250]
        df = df.copy()
        for p in periods:
            df[f"ma{p}"] = df["close"].rolling(window=p).mean()
        return df

    @staticmethod
    def calc_volume_ma(df: pd.DataFrame, periods: Optional[list] = None) -> pd.DataFrame:
        """
        计算成交量均线

        Args:
            df: 包含 volume 列的 DataFrame
            periods: 均量周期列表，默认 [5, 20, 60]

        Returns:
            包含成交量均线的 DataFrame
        """
        if periods is None:
            periods = [5, 20, 60]
        df = df.copy()
        for p in periods:
            df[f"volume_ma{p}"] = df["volume"].rolling(window=p).mean()
        return df

    @staticmethod
    def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算 ATR（平均真实波幅）

        Args:
            df: 包含 high, low, close 列的 DataFrame
            period: 周期（默认 14）

        Returns:
            包含 ATR 指标的 DataFrame
        """
        df = df.copy()
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()

        df["tr"] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df[f"atr_{period}"] = df["tr"].rolling(window=period).mean()
        return df

    @staticmethod
    def calc_obv(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 OBV（能量潮指标）

        Args:
            df: 包含 close, volume 列的 DataFrame

        Returns:
            包含 OBV 指标的 DataFrame
        """
        df = df.copy()
        df["obv"] = (df["volume"] * (~df["close"].diff().le(0) * 2 - 1)).cumsum()
        return df

    @staticmethod
    def calc_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            包含所有技术指标的 DataFrame
        """
        df = TechnicalIndicators.calc_ma(df)
        df = TechnicalIndicators.calc_macd(df)
        df = TechnicalIndicators.calc_kdj(df)
        df = TechnicalIndicators.calc_rsi(df)
        df = TechnicalIndicators.calc_bollinger(df)
        df = TechnicalIndicators.calc_volume_ma(df)
        df = TechnicalIndicators.calc_atr(df)
        df = TechnicalIndicators.calc_obv(df)
        return df

    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取最新技术指标摘要

        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            最新指标摘要字典
        """
        if df is None or df.empty:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        result = {}

        # MACD
        if "macd_dif" in df.columns:
            result["macd"] = {
                "dif": round(latest.get("macd_dif", 0), 4),
                "dea": round(latest.get("macd_dea", 0), 4),
                "hist": round(latest.get("macd_hist", 0), 4),
                "signal": "金叉" if latest.get("macd_dif", 0) > latest.get("macd_dea", 0)
                and prev.get("macd_dif", 0) <= prev.get("macd_dea", 0)
                else "死叉" if latest.get("macd_dif", 0) < latest.get("macd_dea", 0)
                and prev.get("macd_dif", 0) >= prev.get("macd_dea", 0)
                else "多头" if latest.get("macd_dif", 0) > latest.get("macd_dea", 0)
                else "空头",
                "zero_position": "零轴上方" if latest.get("macd_dif", 0) > 0 else "零轴下方",
            }

        # KDJ
        if "kdj_k" in df.columns:
            k_val = latest.get("kdj_k", 50)
            d_val = latest.get("kdj_d", 50)
            j_val = latest.get("kdj_j", 50)
            result["kdj"] = {
                "k": round(k_val, 2),
                "d": round(d_val, 2),
                "j": round(j_val, 2),
                "status": "超买" if k_val > 80 and d_val > 80
                else "超卖" if k_val < 20 and d_val < 20
                else "金叉" if k_val > d_val and prev.get("kdj_k", 50) <= prev.get("kdj_d", 50)
                else "死叉" if k_val < d_val and prev.get("kdj_k", 50) >= prev.get("kdj_d", 50)
                else "正常",
            }

        # RSI
        if "rsi_14" in df.columns:
            rsi_val = latest.get("rsi_14", 50)
            result["rsi"] = {
                "value": round(rsi_val, 2),
                "status": "超买" if rsi_val > 70
                else "超卖" if rsi_val < 30
                else "中性",
            }

        # 布林带
        if "boll_mid" in df.columns:
            close = latest.get("close", 0)
            upper = latest.get("boll_upper", 0)
            lower = latest.get("boll_lower", 0)
            mid = latest.get("boll_mid", 0)
            width = latest.get("boll_width", 0)
            position = latest.get("boll_position", 0.5)
            result["bollinger"] = {
                "upper": round(upper, 2),
                "mid": round(mid, 2),
                "lower": round(lower, 2),
                "width": round(width, 2),
                "position": round(position, 2),
                "status": "上轨附近" if position > 0.8
                else "下轨附近" if position < 0.2
                else "中轨附近",
            }

        # 均线系统
        ma_info = {}
        for p in [5, 10, 20, 30, 60]:
            col = f"ma{p}"
            if col in df.columns:
                ma_val = latest.get(col, 0)
                ma_info[f"MA{p}"] = round(ma_val, 2) if ma_val else None
        if ma_info:
            result["ma"] = ma_info

        # 均线排列判断
        ma_keys = [f"ma{p}" for p in [5, 10, 20, 30, 60]]
        available_mas = [k for k in ma_keys if k in df.columns and not pd.isna(latest.get(k))]
        if len(available_mas) >= 3:
            ma_values = [latest.get(k, 0) for k in available_mas]
            result["ma_alignment"] = "多头排列" if all(ma_values[i] > ma_values[i + 1] for i in range(len(ma_values) - 1)) \
                else "空头排列" if all(ma_values[i] < ma_values[i + 1] for i in range(len(ma_values) - 1)) \
                else "缠绕震荡"

        # ATR
        if "atr_14" in df.columns:
            atr_val = latest.get("atr_14", 0)
            close = latest.get("close", 1)
            result["atr"] = {
                "value": round(atr_val, 4),
                "ratio": round(atr_val / close * 100, 2) if close else 0,
            }

        # OBV
        if "obv" in df.columns:
            obv_val = latest.get("obv", 0)
            obv_prev = prev.get("obv", 0)
            result["obv"] = {
                "value": round(obv_val, 2),
                "trend": "上升" if obv_val > obv_prev else "下降",
            }

        # 成交量分析
        if "volume_ma5" in df.columns:
            vol = latest.get("volume", 0)
            vol_ma5 = latest.get("volume_ma5", 0)
            vol_ma20 = latest.get("volume_ma20", 0)
            result["volume_analysis"] = {
                "current": vol,
                "ma5": vol_ma5,
                "ma20": vol_ma20,
                "vs_ma5": f"{vol / vol_ma5:.2f}x" if vol_ma5 else "N/A",
                "vs_ma20": f"{vol / vol_ma20:.2f}x" if vol_ma20 else "N/A",
                "status": "放量" if vol > vol_ma5 * 1.5
                else "缩量" if vol < vol_ma5 * 0.5
                else "平量",
            }

        # 区间统计
        if len(df) > 1:
            result["range_stats"] = {
                "period_high": round(df["high"].max(), 2),
                "period_low": round(df["low"].min(), 2),
                "period_change": round((df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100, 2),
                "volatility": round(df["close"].pct_change().std() * np.sqrt(252) * 100, 2),
            }

        return result

    @staticmethod
    def get_market_signal(df: pd.DataFrame) -> Dict[str, Any]:
        """
        综合判断市场信号

        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            综合信号字典
        """
        indicators = TechnicalIndicators.get_latest_indicators(df)
        signals = []
        score = 0

        # MACD 信号
        macd = indicators.get("macd", {})
        if macd.get("signal") in ("金叉", "多头"):
            signals.append(("MACD", "看多", 1))
            score += 1
        elif macd.get("signal") in ("死叉", "空头"):
            signals.append(("MACD", "看空", -1))
            score -= 1
        else:
            signals.append(("MACD", "中性", 0))

        # KDJ 信号
        kdj = indicators.get("kdj", {})
        if kdj.get("status") == "超卖":
            signals.append(("KDJ", "超卖反弹", 1))
            score += 1
        elif kdj.get("status") == "超买":
            signals.append(("KDJ", "超买回调", -1))
            score -= 1
        elif kdj.get("status") == "金叉":
            signals.append(("KDJ", "看多", 1))
            score += 1
        elif kdj.get("status") == "死叉":
            signals.append(("KDJ", "看空", -1))
            score -= 1
        else:
            signals.append(("KDJ", "中性", 0))

        # RSI 信号
        rsi = indicators.get("rsi", {})
        if rsi.get("status") == "超卖":
            signals.append(("RSI", "超卖反弹", 1))
            score += 1
        elif rsi.get("status") == "超买":
            signals.append(("RSI", "超买回调", -1))
            score -= 1
        else:
            signals.append(("RSI", "中性", 0))

        # 均线排列信号
        alignment = indicators.get("ma_alignment", "")
        if alignment == "多头排列":
            signals.append(("均线", "多头排列", 1))
            score += 1
        elif alignment == "空头排列":
            signals.append(("均线", "空头排列", -1))
            score -= 1
        else:
            signals.append(("均线", "缠绕", 0))

        # 布林带信号
        boll = indicators.get("bollinger", {})
        if boll.get("status") == "下轨附近":
            signals.append(("布林带", "下轨支撑", 1))
            score += 1
        elif boll.get("status") == "上轨附近":
            signals.append(("布林带", "上轨压力", -1))
            score -= 1
        else:
            signals.append(("布林带", "中轨附近", 0))

        # 成交量信号
        vol = indicators.get("volume_analysis", {})
        if vol.get("status") == "放量" and score > 0:
            signals.append(("成交量", "放量上涨", 1))
            score += 1
        elif vol.get("status") == "放量" and score < 0:
            signals.append(("成交量", "放量下跌", -1))
            score -= 1

        # 综合判断
        if score >= 3:
            overall = "强烈看多 📈"
            confidence = "高"
        elif score >= 1:
            overall = "温和看多 ↗️"
            confidence = "中"
        elif score <= -3:
            overall = "强烈看空 📉"
            confidence = "高"
        elif score <= -1:
            overall = "温和看空 ↘️"
            confidence = "中"
        else:
            overall = "多空均衡 ⚖️"
            confidence = "低"

        return {
            "overall_signal": overall,
            "composite_score": score,
            "confidence": confidence,
            "signals": signals,
            "max_score": 6,
        }
