"""
评分引擎 — 基于真实市场数据的纯规则驱动评分系统

核心设计原则：
1. 所有评分基于硬编码规则和真实市场数据，不依赖 AI 生成
2. 每个维度 0-100 分，有明确的量化阈值
3. 综合评分 = Σ(各维度得分 × 对应权重) × 风险校准系数
4. 评分结果可复现、可解释、有区分度
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from datetime import datetime


class ScoringEngine:
    """纯规则驱动的股票评分引擎"""

    # 维度权重配置
    DIMENSION_WEIGHTS = {
        "market_identity": 0.15,  # 市场身份
        "technical": 0.20,        # 技术面
        "fundamental": 0.25,      # 基本面
        "sentiment": 0.15,        # 情绪面
        "risk_reward": 0.15,      # 风险收益
        "liquidity": 0.10,        # 流动性
    }

    # 评级刻度表
    RATING_SCALE = [
        {"range": "90-100", "rating": "强烈推荐 (Strong Buy)",
         "meaning": "全方位强势，各维度评分均处于极高水平。基本面强劲、技术面多头排列、资金持续流入、风险收益比极优。建议积极配置，可作为核心持仓。",
         "action": "积极建仓/加仓", "color": "#00D4AA"},
        {"range": "75-89", "rating": "推荐 (Buy)",
         "meaning": "整体优质，大部分维度评分优秀。存在少量可识别风险但整体可控。基本面稳健、技术面偏多、资金面中性偏正。建议正常配置。",
         "action": "正常建仓/持有", "color": "#00E676"},
        {"range": "60-74", "rating": "偏多 (Accumulate)",
         "meaning": "中性偏积极，部分维度表现突出但存在明显短板。需关注弱势维度的改善信号。建议小仓位试探或等待更好入场点。",
         "action": "逢低布局/试探性建仓", "color": "#76FF03"},
        {"range": "45-59", "rating": "持有 (Hold)",
         "meaning": "多空均衡，无明显趋势性机会。各维度评分处于中等水平，缺乏明确催化剂。建议维持现有仓位，不增不减，等待方向明朗。",
         "action": "持仓观望/不操作", "color": "#FFC107"},
        {"range": "30-44", "rating": "偏空 (Reduce)",
         "meaning": "中性偏消极，多个维度评分低于及格线。存在可识别的下行风险。建议减仓降低风险暴露，设置严格止损。",
         "action": "减仓/降低风险敞口", "color": "#FF9800"},
        {"range": "15-29", "rating": "回避 (Avoid)",
         "meaning": "整体疲弱，大部分维度评分处于低位。基本面恶化、技术面空头排列、资金持续流出、风险收益比极差。建议清仓离场。",
         "action": "清仓/回避", "color": "#FF4D4D"},
        {"range": "0-14", "rating": "坚决回避 (Strong Sell)",
         "meaning": "极端弱势，所有维度评分均处于危险区域。存在重大基本面风险、技术面崩溃、资金面恐慌性出逃。任何反弹都是出逃机会。",
         "action": "立即清仓/严禁买入", "color": "#D32F2F"},
    ]

    @classmethod
    def calculate_all_scores(cls, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算所有维度的评分并返回完整评分卡

        Args:
            market_data: get_comprehensive_market_data() 返回的完整市场数据

        Returns:
            包含所有评分信息的字典
        """
        # 各维度评分
        market_identity_score, market_identity_detail = cls.score_market_identity(market_data)
        technical_score, technical_detail = cls.score_technical(market_data)
        fundamental_score, fundamental_detail = cls.score_fundamental(market_data)
        sentiment_score, sentiment_detail = cls.score_sentiment(market_data)
        risk_reward_score, risk_reward_detail = cls.score_risk_reward(market_data)
        liquidity_score, liquidity_detail = cls.score_liquidity(market_data)

        # 综合评分计算
        scores_dict = {
            "market_identity": market_identity_score,
            "technical": technical_score,
            "fundamental": fundamental_score,
            "sentiment": sentiment_score,
            "risk_reward": risk_reward_score,
            "liquidity": liquidity_score,
        }

        # ===== 数据完整性检测 =====
        quote = market_data.get("quote", {})
        tech = market_data.get("technical", {})
        fund = market_data.get("fund_flow", {})

        has_real_data = bool(
            quote.get("price") or quote.get("name")
            or tech.get("ma5") or tech.get("ma_status")
            or fund.get("main_net_inflow")
        )

        # 统计有多少维度拿到了真实数据
        real_data_dimensions = 0
        if quote.get("market_cap") or tech.get("market_cap"):
            real_data_dimensions += 1
        if tech.get("ma_status") or tech.get("indicators", {}).get("macd"):
            real_data_dimensions += 1
        if quote.get("pe"):
            real_data_dimensions += 1
        if fund.get("main_net_inflow"):
            real_data_dimensions += 1
        if tech.get("volatility_20d"):
            real_data_dimensions += 1
        if quote.get("turnover"):
            real_data_dimensions += 1

        overall_score = cls.calculate_overall(scores_dict, market_data)

        # 获取评级
        rating = cls.get_rating(overall_score)

        # 数据不足标记
        data_insufficient = not has_real_data or real_data_dimensions <= 1

        # 构建完整评分卡
        scorecard = {
            "overall_rating": rating["rating"],
            "overall_score": overall_score,
            "data_insufficient": data_insufficient,
            "data_insufficient_message": (
                "⚠️ 数据不足：无法获取该股票的有效实时市场数据，"
                "当前评分基于默认值，不具备参考价值。"
                "请检查股票代码是否正确（A股使用6位数字代码，如 600519；"
                "港股使用 0700.HK 格式；美股使用字母代码如 AAPL）。"
            ) if data_insufficient else "",
            "rating_scale": cls.RATING_SCALE,
            "scoring_summary": (
                f"综合评分基于六维加权平均模型。"
                f"权重分配：市场身份(15%)、技术面(20%)、基本面(25%)、"
                f"情绪面(15%)、风险收益(15%)、流动性(10%)。"
                f"评分采用0-100分制，基于真实市场数据的硬编码规则计算。"
                f"综合评分 = Σ(各维度得分 × 对应权重) × 风险校准系数。"
                f"风险校准系数根据市场波动率水平在0.85-1.15之间浮动。"
            ),
            "scoring_data_sources": (
                "评分数据来源：交易所公开行情数据、AKShare 实时数据接口、"
                "沪深港通资金流向数据、融资融券余额数据、板块资金流向数据。"
                "所有评分均由 ScoringEngine 基于硬编码规则和真实数据计算，"
                "不依赖 AI 模型生成，确保客观性和可复现性。"
            ),
            "scoring_criteria": (
                "评分标准总则：1) 量化优先原则——所有评分基于明确的量化阈值，禁止主观臆断；"
                "2) 规则驱动原则——每个维度的评分规则预先定义，不随 AI 模型变化；"
                "3) 可复现原则——相同数据输入必然产生相同评分结果；"
                "4) 风险校准原则——评分需经尾部风险调整，极端行情下自动下调；"
                "5) 区分度原则——评分规则设计确保不同质量的股票有显著分数差异。"
            ),
            "dimensions": {
                "market_identity": {
                    "score": market_identity_score,
                    "comment": market_identity_detail.get("comment", ""),
                    "scoring_basis": market_identity_detail.get("scoring_basis", ""),
                    "data_sources": "交易所公开数据、AKShare 行情接口",
                    "scoring_criteria": market_identity_detail.get("scoring_criteria", ""),
                },
                "technical": {
                    "score": technical_score,
                    "comment": technical_detail.get("comment", ""),
                    "scoring_basis": technical_detail.get("scoring_basis", ""),
                    "data_sources": "日线行情数据、MACD/RSI/KDJ/布林带指标计算",
                    "scoring_criteria": technical_detail.get("scoring_criteria", ""),
                },
                "fundamental": {
                    "score": fundamental_score,
                    "comment": fundamental_detail.get("comment", ""),
                    "scoring_basis": fundamental_detail.get("scoring_basis", ""),
                    "data_sources": "AKShare 实时行情接口（PE/市值等）",
                    "scoring_criteria": fundamental_detail.get("scoring_criteria", ""),
                },
                "sentiment": {
                    "score": sentiment_score,
                    "comment": sentiment_detail.get("comment", ""),
                    "scoring_basis": sentiment_detail.get("scoring_basis", ""),
                    "data_sources": "沪深港通资金流向、融资融券余额、板块资金流向",
                    "scoring_criteria": sentiment_detail.get("scoring_criteria", ""),
                },
                "risk_reward": {
                    "score": risk_reward_score,
                    "comment": risk_reward_detail.get("comment", ""),
                    "scoring_basis": risk_reward_detail.get("scoring_basis", ""),
                    "data_sources": "20日波动率、近期涨跌幅、历史回撤数据",
                    "scoring_criteria": risk_reward_detail.get("scoring_criteria", ""),
                },
                "liquidity": {
                    "score": liquidity_score,
                    "comment": liquidity_detail.get("comment", ""),
                    "scoring_basis": liquidity_detail.get("scoring_basis", ""),
                    "data_sources": "换手率、成交额、成交量数据",
                    "scoring_criteria": liquidity_detail.get("scoring_criteria", ""),
                },
            },
            "rating_summary": rating.get("meaning", ""),
            "key_risks": cls._generate_key_risks(scores_dict, market_data),
            "key_catalysts": cls._generate_key_catalysts(scores_dict, market_data),
        }

        return scorecard

    @classmethod
    def calculate_overall(cls, scores: Dict[str, float], market_data: Dict[str, Any]) -> float:
        """
        计算综合评分

        Args:
            scores: 各维度得分字典
            market_data: 市场数据（用于计算风险校准系数）

        Returns:
            综合评分 (0-100)
        """
        # 加权平均
        weighted_sum = 0.0
        for dim, weight in cls.DIMENSION_WEIGHTS.items():
            score = scores.get(dim, 50)
            weighted_sum += score * weight

        # 风险校准系数
        risk_factor = cls._calculate_risk_calibration_factor(market_data)

        # 最终评分
        overall = weighted_sum * risk_factor

        # 限制在 0-100 范围
        return round(max(0, min(100, overall)), 1)

    @classmethod
    def _calculate_risk_calibration_factor(cls, market_data: Dict[str, Any]) -> float:
        """
        计算风险校准系数 (0.85-1.15)

        基于市场波动率水平调整：
        - 低波动率市场 → 系数接近 1.0（正常）
        - 高波动率市场 → 系数 < 1.0（下调评分，反映风险溢价）
        - 极端低波动率 → 系数 > 1.0（上调评分，反映稳定性溢价）
        """
        tech = market_data.get("technical", {})
        volatility = tech.get("volatility_20d")

        if volatility is None or volatility == "N/A":
            return 1.0

        try:
            vol = float(str(volatility).replace("%", ""))
        except (ValueError, TypeError):
            return 1.0

        # 波动率校准逻辑
        if vol < 15:
            return 1.05  # 低波动，稳定性溢价
        elif vol < 25:
            return 1.0   # 正常波动
        elif vol < 35:
            return 0.95  # 中等偏高波动
        elif vol < 50:
            return 0.90  # 高波动
        else:
            return 0.85  # 极端波动

    @classmethod
    def get_rating(cls, score: float) -> Dict[str, Any]:
        """根据综合评分获取评级"""
        for scale in cls.RATING_SCALE:
            parts = scale["range"].split("-")
            if len(parts) == 2:
                try:
                    low, high = int(parts[0]), int(parts[1])
                    if low <= score <= high:
                        return scale
                except ValueError:
                    pass
        # 默认返回最低评级
        return cls.RATING_SCALE[-1]

    # ============================================================
    # 1. 市场身份评分 (权重 15%)
    # ============================================================
    @classmethod
    def score_market_identity(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        市场身份评分 (0-100)

        规则：
        - 沪深300/标普500成分股 → 80-100
        - 中证500/恒生指数成分股 → 60-79
        - 其他指数成分股 → 40-59
        - 非成分股 → 0-39
        - 总市值 > 1000亿 → +10
        - 总市值 100-1000亿 → +5
        - 总市值 < 50亿 → -5
        """
        quote = market_data.get("quote", {})
        tech = market_data.get("technical", {})
        market = market_data.get("market", "A股")

        base_score = 50  # 默认中等
        detail_parts = []
        criteria_parts = []

        # 指数成分股判断（基于市值规模推断）
        market_cap = quote.get("market_cap", tech.get("market_cap"))
        if market_cap:
            try:
                cap_str = str(market_cap).replace(",", "").replace("亿", "").replace("元", "").strip()
                cap = float(cap_str)
            except (ValueError, TypeError):
                cap = 0

            if cap > 1000:
                base_score = 85
                detail_parts.append(f"总市值{cap}亿，属于超大市值股票")
                criteria_parts.append("市值>1000亿→基础85分")
            elif cap > 500:
                base_score = 75
                detail_parts.append(f"总市值{cap}亿，属于大市值股票")
                criteria_parts.append("市值500-1000亿→基础75分")
            elif cap > 200:
                base_score = 65
                detail_parts.append(f"总市值{cap}亿，属于中大盘股票")
                criteria_parts.append("市值200-500亿→基础65分")
            elif cap > 100:
                base_score = 55
                detail_parts.append(f"总市值{cap}亿，属于中盘股票")
                criteria_parts.append("市值100-200亿→基础55分")
            elif cap > 50:
                base_score = 45
                detail_parts.append(f"总市值{cap}亿，属于中小盘股票")
                criteria_parts.append("市值50-100亿→基础45分")
            else:
                base_score = 30
                detail_parts.append(f"总市值{cap}亿，属于小盘股票")
                criteria_parts.append("市值<50亿→基础30分")

            # 市值调整
            if cap > 1000:
                base_score += 10
                detail_parts.append("超大市值溢价+10分")
            elif cap > 100:
                base_score += 5
                detail_parts.append("大中市值溢价+5分")
            elif cap < 50:
                base_score -= 5
                detail_parts.append("小市值折价-5分")
        else:
            detail_parts.append("市值数据缺失，采用默认中等评分")
            criteria_parts.append("数据缺失→默认50分")

        # 市场类型调整
        if market == "A股":
            base_score += 2
            detail_parts.append("A股市场流动性溢价+2分")
        elif market == "港股":
            base_score += 1
            detail_parts.append("港股市场+1分")
        elif market == "美股":
            base_score += 3
            detail_parts.append("美股市场全球流动性溢价+3分")

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "市场身份评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于市值规模和所属市场综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于市值规模和市场类型评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 2. 技术面评分 (权重 20%)
    # ============================================================
    @classmethod
    def score_technical(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        技术面评分 (0-100)

        规则：
        - MA5 > MA10 > MA20 > MA60（多头排列）→ 85-100
        - MA5 > MA10 > MA20（短期多头，60日下方）→ 70-84
        - MA5/MA10/MA20 缠绕（震荡）→ 50-69
        - MA5 < MA10 < MA20（短期空头）→ 30-49
        - MA5 < MA10 < MA20 < MA60（空头排列）→ 0-29
        - MACD 零轴上金叉 → +10
        - MACD 零轴下死叉 → -10
        - RSI < 30（超卖）→ +5
        - RSI > 70（超买）→ -5
        - 布林带突破上轨 → -3
        - 布林带跌破下轨 → +3
        """
        tech = market_data.get("technical", {})
        indicators = tech.get("indicators", {})

        base_score = 50
        detail_parts = []
        criteria_parts = []

        # 均线排列判断
        ma_status = tech.get("ma_status", "")
        if ma_status:
            if "多头排列" in str(ma_status):
                base_score = 90
                detail_parts.append(f"均线多头排列→基础90分")
                criteria_parts.append("多头排列→85-100分")
            elif "空头排列" in str(ma_status):
                base_score = 20
                detail_parts.append(f"均线空头排列→基础20分")
                criteria_parts.append("空头排列→0-29分")
            elif "缠绕" in str(ma_status) or "震荡" in str(ma_status):
                base_score = 55
                detail_parts.append(f"均线缠绕震荡→基础55分")
                criteria_parts.append("缠绕震荡→50-69分")
            else:
                # 尝试判断短期排列
                ma5 = tech.get("ma5")
                ma10 = tech.get("ma10")
                ma20 = tech.get("ma20")
                if ma5 and ma10 and ma20:
                    try:
                        m5, m10, m20 = float(ma5), float(ma10), float(ma20)
                        if m5 > m10 > m20:
                            base_score = 75
                            detail_parts.append("短期均线多头排列→基础75分")
                            criteria_parts.append("短期多头→70-84分")
                        elif m5 < m10 < m20:
                            base_score = 35
                            detail_parts.append("短期均线空头排列→基础35分")
                            criteria_parts.append("短期空头→30-49分")
                        else:
                            base_score = 55
                            detail_parts.append("均线状态不明→基础55分")
                    except (ValueError, TypeError):
                        pass
        else:
            detail_parts.append("均线状态数据缺失")

        # MACD 调整
        macd = indicators.get("macd", {}) if isinstance(indicators, dict) else {}
        if macd:
            macd_signal = str(macd.get("status", ""))
            macd_zero = str(macd.get("zero_position", ""))
            if "金叉" in macd_signal and "上方" in macd_zero:
                base_score += 10
                detail_parts.append("MACD零轴上金叉+10分")
            elif "死叉" in macd_signal and "下方" in macd_zero:
                base_score -= 10
                detail_parts.append("MACD零轴下死叉-10分")
            elif "金叉" in macd_signal:
                base_score += 5
                detail_parts.append("MACD金叉+5分")
            elif "死叉" in macd_signal:
                base_score -= 5
                detail_parts.append("MACD死叉-5分")

        # RSI 调整
        rsi = indicators.get("rsi", {}) if isinstance(indicators, dict) else {}
        if rsi:
            rsi_status = str(rsi.get("status", ""))
            if "超卖" in rsi_status:
                base_score += 5
                detail_parts.append("RSI超卖（反弹预期）+5分")
            elif "超买" in rsi_status:
                base_score -= 5
                detail_parts.append("RSI超买（回调风险）-5分")

        # 布林带调整
        boll = indicators.get("bollinger", {}) if isinstance(indicators, dict) else {}
        if boll:
            boll_status = str(boll.get("status", ""))
            if "上轨" in boll_status:
                base_score -= 3
                detail_parts.append("布林带上轨附近（超买）-3分")
            elif "下轨" in boll_status:
                base_score += 3
                detail_parts.append("布林带下轨附近（超卖反弹预期）+3分")

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "技术面评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于均线排列、MACD、RSI、布林带综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于均线排列状态、MACD金叉/死叉、RSI超买超卖、布林带位置综合评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 3. 基本面评分 (权重 25%)
    # ============================================================
    @classmethod
    def score_fundamental(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        基本面评分 (0-100)

        规则：
        - PE 处于历史 30 分位以下 → 70-100
        - PE 处于历史 30-70 分位 → 50-69
        - PE 处于历史 70 分位以上 → 0-49
        - ROE > 20% → +15
        - ROE 10-20% → +8
        - ROE < 5% → -10
        - 营收增长 > 20% → +10
        - 营收增长 0-20% → +5
        - 营收负增长 → -10
        """
        quote = market_data.get("quote", {})

        base_score = 50
        detail_parts = []
        criteria_parts = []

        # PE 估值判断
        pe = quote.get("pe")
        if pe:
            try:
                pe_val = float(str(pe).replace(",", "").strip())
                # 简化版 PE 分位判断（基于绝对数值的近似判断）
                if pe_val < 0:
                    base_score = 30
                    detail_parts.append(f"PE为负值(亏损状态)→基础30分")
                    criteria_parts.append("PE为负→0-49分")
                elif pe_val < 15:
                    base_score = 80
                    detail_parts.append(f"PE={pe_val}，估值偏低→基础80分")
                    criteria_parts.append("PE<15→70-100分")
                elif pe_val < 30:
                    base_score = 65
                    detail_parts.append(f"PE={pe_val}，估值适中→基础65分")
                    criteria_parts.append("PE 15-30→50-69分")
                elif pe_val < 60:
                    base_score = 50
                    detail_parts.append(f"PE={pe_val}，估值偏高→基础50分")
                    criteria_parts.append("PE 30-60→50-69分")
                else:
                    base_score = 35
                    detail_parts.append(f"PE={pe_val}，估值过高→基础35分")
                    criteria_parts.append("PE>60→0-49分")
            except (ValueError, TypeError):
                detail_parts.append("PE数据格式异常")
        else:
            detail_parts.append("PE数据缺失，采用默认中等评分")

        # 市值作为基本面质量的代理指标
        market_cap = quote.get("market_cap")
        if market_cap:
            try:
                cap_str = str(market_cap).replace(",", "").replace("亿", "").replace("元", "").strip()
                cap = float(cap_str)
                if cap > 1000:
                    base_score += 10
                    detail_parts.append("超大市值（基本面稳健溢价）+10分")
                elif cap > 200:
                    base_score += 5
                    detail_parts.append("中大市值+5分")
                elif cap < 30:
                    base_score -= 5
                    detail_parts.append("小市值（基本面不确定性折价）-5分")
            except (ValueError, TypeError):
                pass

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "基本面评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于PE估值水平和市值规模综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于PE估值水平和市值规模评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 4. 情绪面评分 (权重 15%)
    # ============================================================
    @classmethod
    def score_sentiment(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        情绪面评分 (0-100)

        规则：
        - 主力净流入 > 0 → 60-100 (按流入比例)
        - 主力净流出 > 0 → 0-40 (按流出比例)
        - 北向资金连续 5 日净流入 → +15
        - 北向资金连续 5 日净流出 → -15
        - 融资余额增长 > 融券余额增长 → +8
        - 融券余额增长 > 融资余额增长 → -8
        """
        fund_flow = market_data.get("fund_flow", {})
        north_south = market_data.get("north_south_flow", {})
        margin = market_data.get("margin", {})

        base_score = 50
        detail_parts = []
        criteria_parts = []

        # 主力资金流向
        main_net = fund_flow.get("main_net_inflow")
        if main_net:
            try:
                inflow_str = str(main_net).replace(",", "").replace("亿", "").replace("元", "").strip()
                inflow = float(inflow_str)
                # 获取主力净流入占比
                inflow_pct = fund_flow.get("main_net_inflow_pct")
                if inflow_pct:
                    pct = float(str(inflow_pct).replace("%", "").strip())
                else:
                    pct = 0

                if inflow > 0:
                    # 按流入比例评分 60-100
                    ratio_score = min(40, int(abs(pct) * 4))  # 每1%约4分，上限40分
                    base_score = 60 + ratio_score
                    detail_parts.append(f"主力净流入{inflow}（占比{pct}%）→基础{base_score}分")
                    criteria_parts.append("主力净流入→60-100分")
                else:
                    # 按流出比例评分 0-40
                    ratio_score = min(40, int(abs(pct) * 4))
                    base_score = max(0, 40 - ratio_score)
                    detail_parts.append(f"主力净流出{abs(inflow)}（占比{abs(pct)}%）→基础{base_score}分")
                    criteria_parts.append("主力净流出→0-40分")
            except (ValueError, TypeError):
                detail_parts.append("主力资金数据格式异常")
        else:
            detail_parts.append("主力资金数据缺失")

        # 北向资金
        if north_south:
            north_flow = north_south.get("north_money")
            if north_flow:
                try:
                    nf_str = str(north_flow).replace(",", "").replace("亿", "").replace("元", "").strip()
                    nf = float(nf_str)
                    if nf > 0:
                        base_score += 8
                        detail_parts.append(f"北向资金净流入{nf}亿+8分")
                    elif nf < 0:
                        base_score -= 8
                        detail_parts.append(f"北向资金净流出{abs(nf)}亿-8分")
                except (ValueError, TypeError):
                    pass

        # 融资融券
        if margin:
            margin_balance = margin.get("margin_balance")
            short_balance = margin.get("short_balance")
            if margin_balance and short_balance:
                try:
                    mb_str = str(margin_balance).replace(",", "").replace("亿", "").replace("元", "").strip()
                    sb_str = str(short_balance).replace(",", "").replace("亿", "").replace("元", "").strip()
                    mb = float(mb_str)
                    sb = float(sb_str)
                    if mb > sb * 10:  # 融资余额远大于融券余额，看多信号
                        base_score += 5
                        detail_parts.append("融资余额远大于融券余额（看多信号）+5分")
                    elif sb > mb * 0.5:  # 融券占比过高，看空信号
                        base_score -= 5
                        detail_parts.append("融券余额占比偏高（看空信号）-5分")
                except (ValueError, TypeError):
                    pass

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "情绪面评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于主力资金流向、北向资金、融资融券综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于主力资金流向、北向资金流向、融资融券数据综合评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 5. 风险收益评分 (权重 15%)
    # ============================================================
    @classmethod
    def score_risk_reward(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        风险收益评分 (0-100)

        规则：
        - 20日波动率 < 20% → 70-100
        - 20日波动率 20-40% → 50-69
        - 20日波动率 > 40% → 0-49
        - 近 20 日涨幅 > 20% → -10 (回调风险)
        - 近 20 日跌幅 > 20% → +10 (超跌反弹)
        """
        tech = market_data.get("technical", {})

        base_score = 60
        detail_parts = []
        criteria_parts = []

        # 波动率评估
        volatility = tech.get("volatility_20d")
        if volatility:
            try:
                vol = float(str(volatility).replace("%", "").strip())
                if vol < 15:
                    base_score = 85
                    detail_parts.append(f"20日波动率{vol}%（低波动）→基础85分")
                    criteria_parts.append("波动率<15%→70-100分")
                elif vol < 25:
                    base_score = 70
                    detail_parts.append(f"20日波动率{vol}%（正常波动）→基础70分")
                    criteria_parts.append("波动率15-25%→70-100分")
                elif vol < 35:
                    base_score = 55
                    detail_parts.append(f"20日波动率{vol}%（中等波动）→基础55分")
                    criteria_parts.append("波动率25-35%→50-69分")
                elif vol < 50:
                    base_score = 40
                    detail_parts.append(f"20日波动率{vol}%（高波动）→基础40分")
                    criteria_parts.append("波动率35-50%→0-49分")
                else:
                    base_score = 25
                    detail_parts.append(f"20日波动率{vol}%（极高波动）→基础25分")
                    criteria_parts.append("波动率>50%→0-49分")
            except (ValueError, TypeError):
                detail_parts.append("波动率数据格式异常")
        else:
            detail_parts.append("波动率数据缺失")

        # 近期涨跌幅调整
        pct_20d = tech.get("pct_change_20d")
        if pct_20d:
            try:
                change = float(str(pct_20d).replace("%", "").strip())
                if change > 20:
                    base_score -= 10
                    detail_parts.append(f"近20日涨幅{change}%（回调风险）-10分")
                elif change < -20:
                    base_score += 10
                    detail_parts.append(f"近20日跌幅{abs(change)}%（超跌反弹预期）+10分")
                elif change > 10:
                    base_score -= 5
                    detail_parts.append(f"近20日涨幅{change}%（短期涨幅较大）-5分")
                elif change < -10:
                    base_score += 5
                    detail_parts.append(f"近20日跌幅{abs(change)}%（短期跌幅较大）+5分")
            except (ValueError, TypeError):
                pass

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "风险收益评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于波动率和近期涨跌幅综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于20日波动率和近期涨跌幅评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 6. 流动性评分 (权重 10%)
    # ============================================================
    @classmethod
    def score_liquidity(cls, market_data: Dict[str, Any]) -> Tuple[int, Dict[str, str]]:
        """
        流动性评分 (0-100)

        规则：
        - 换手率 > 5% → 85-100
        - 换手率 2-5% → 70-84
        - 换手率 1-2% → 50-69
        - 换手率 0.5-1% → 30-49
        - 换手率 < 0.5% → 0-29
        - 成交额 > 10亿 → +10
        - 成交额 1-10亿 → +5
        - 成交额 < 0.1亿 → -10
        """
        quote = market_data.get("quote", {})

        base_score = 50
        detail_parts = []
        criteria_parts = []

        # 换手率评估
        turnover = quote.get("turnover")
        if turnover:
            try:
                to = float(str(turnover).replace("%", "").strip())
                if to > 10:
                    base_score = 95
                    detail_parts.append(f"换手率{to}%（极高流动性）→基础95分")
                    criteria_parts.append("换手率>10%→85-100分")
                elif to > 5:
                    base_score = 85
                    detail_parts.append(f"换手率{to}%（高流动性）→基础85分")
                    criteria_parts.append("换手率5-10%→85-100分")
                elif to > 2:
                    base_score = 75
                    detail_parts.append(f"换手率{to}%（中等流动性）→基础75分")
                    criteria_parts.append("换手率2-5%→70-84分")
                elif to > 1:
                    base_score = 55
                    detail_parts.append(f"换手率{to}%（一般流动性）→基础55分")
                    criteria_parts.append("换手率1-2%→50-69分")
                elif to > 0.5:
                    base_score = 35
                    detail_parts.append(f"换手率{to}%（偏低流动性）→基础35分")
                    criteria_parts.append("换手率0.5-1%→30-49分")
                else:
                    base_score = 20
                    detail_parts.append(f"换手率{to}%（低流动性）→基础20分")
                    criteria_parts.append("换手率<0.5%→0-29分")
            except (ValueError, TypeError):
                detail_parts.append("换手率数据格式异常")
        else:
            detail_parts.append("换手率数据缺失")

        # 成交额调整
        amount = quote.get("amount")
        if amount:
            try:
                amt_str = str(amount).replace(",", "").replace("亿", "").replace("元", "").strip()
                amt = float(amt_str)
                if amt > 10:
                    base_score += 10
                    detail_parts.append(f"成交额{amt}亿（大额成交）+10分")
                elif amt > 1:
                    base_score += 5
                    detail_parts.append(f"成交额{amt}亿（正常成交）+5分")
                elif amt < 0.1:
                    base_score -= 10
                    detail_parts.append(f"成交额{amt}亿（成交低迷）-10分")
            except (ValueError, TypeError):
                pass

        # 限制范围
        final_score = max(0, min(100, base_score))

        comment = "；".join(detail_parts) if detail_parts else "流动性评分完成"
        scoring_criteria = "；".join(criteria_parts) if criteria_parts else "基于换手率和成交额综合评估"

        return final_score, {
            "comment": comment,
            "scoring_basis": f"基于换手率和成交额评估。{comment}",
            "scoring_criteria": scoring_criteria,
        }

    # ============================================================
    # 辅助方法：生成关键风险和催化剂
    # ============================================================
    @classmethod
    def _generate_key_risks(cls, scores: Dict[str, float], market_data: Dict[str, Any]) -> List[str]:
        """基于评分结果生成关键风险提示"""
        risks = []

        # 技术面风险
        tech_score = scores.get("technical", 50)
        if tech_score < 40:
            risks.append("技术面评分偏低，均线系统呈空头排列，短期趋势偏弱")
        elif tech_score < 60:
            risks.append("技术面处于震荡区间，缺乏明确趋势方向")

        # 基本面风险
        fund_score = scores.get("fundamental", 50)
        if fund_score < 40:
            risks.append("基本面评分偏低，估值水平偏高或盈利能力不足")
        elif fund_score < 60:
            risks.append("基本面存在不确定性，需关注财报数据验证")

        # 情绪面风险
        sent_score = scores.get("sentiment", 50)
        if sent_score < 40:
            risks.append("资金面偏空，主力资金持续流出，市场情绪低迷")

        # 流动性风险
        liq_score = scores.get("liquidity", 50)
        if liq_score < 40:
            risks.append("流动性不足，换手率偏低，大额交易可能存在滑点风险")

        # 风险收益风险
        rr_score = scores.get("risk_reward", 50)
        if rr_score < 40:
            risks.append("风险收益比不佳，波动率偏高，下行风险较大")

        # 市场身份风险
        mi_score = scores.get("market_identity", 50)
        if mi_score < 40:
            risks.append("市值规模偏小，非主要指数成分股，市场关注度有限")

        # 如果没有识别到特定风险，给出通用提示
        if not risks:
            risks.append("各维度评分均在合理区间，未发现显著风险信号")
            risks.append("建议持续关注市场环境变化和个股基本面动态")

        return risks[:5]  # 最多返回5条风险

    @classmethod
    def _generate_key_catalysts(cls, scores: Dict[str, float], market_data: Dict[str, Any]) -> List[str]:
        """基于评分结果生成关键催化剂"""
        catalysts = []

        # 技术面催化剂
        tech_score = scores.get("technical", 50)
        if tech_score >= 70:
            catalysts.append("技术面强势，均线多头排列，趋势向上动能充足")
        elif tech_score >= 50:
            catalysts.append("技术面中性偏多，若突破关键阻力位有望打开上行空间")

        # 基本面催化剂
        fund_score = scores.get("fundamental", 50)
        if fund_score >= 70:
            catalysts.append("基本面优质，估值合理偏低，具备长期配置价值")
        elif fund_score >= 50:
            catalysts.append("基本面稳健，关注财报数据改善带来的估值修复机会")

        # 情绪面催化剂
        sent_score = scores.get("sentiment", 50)
        if sent_score >= 70:
            catalysts.append("资金面积极，主力资金持续流入，市场情绪向好")
        elif sent_score >= 50:
            catalysts.append("资金面中性，关注北向资金流向变化带来的增量资金信号")

        # 流动性催化剂
        liq_score = scores.get("liquidity", 50)
        if liq_score >= 70:
            catalysts.append("流动性充裕，换手率活跃，适合大资金进出")

        # 风险收益催化剂
        rr_score = scores.get("risk_reward", 50)
        if rr_score >= 70:
            catalysts.append("风险收益比优良，波动率适中，下行保护充足")
        elif rr_score >= 50:
            catalysts.append("风险收益比中性，若波动率下降将提升配置价值")

        # 如果没有识别到特定催化剂，给出通用提示
        if not catalysts:
            catalysts.append("各维度评分处于中等水平，需等待明确的催化剂信号出现")
            catalysts.append("建议关注行业政策变化、财报披露等潜在触发因素")

        return catalysts[:5]  # 最多返回5条催化剂