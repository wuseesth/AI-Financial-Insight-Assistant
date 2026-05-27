"""
金融分析 Prompt 模板
===================
所有提示词集中管理，便于后续优化和扩展。
支持 i18n 扩展，当前为中文版本。
"""

# ============================================================
# 财经新闻分析 Prompt
# ============================================================

NEWS_ANALYSIS_PROMPT = """
请对以下财经新闻进行专业分析，输出格式必须为 JSON，包含以下字段：

## 分析要求
1. **summary**: 用三句话总结新闻核心内容
2. **sentiment**: 判断利好/利空/中性，并给出置信度（百分比）
3. **industries**: 涉及的相关行业列表
4. **companies**: 涉及的相关公司列表
5. **risks**: 风险提示列表
6. **market_impact**: 对市场的影响分析（短期/长期）
7. **key_points**: 关键要点列表
8. **recommendation**: 投资建议（谨慎/关注/观望/回避）

## 输出格式
请严格按以下 JSON 格式输出，不要包含其他内容：
{{
    "summary": "三句话总结，每句用句号分隔。",
    "sentiment": {{
        "judgment": "利好/利空/中性",
        "confidence": 85,
        "reason": "判断依据"
    }},
    "industries": ["行业1", "行业2"],
    "companies": ["公司1", "公司2"],
    "risks": ["风险1", "风险2"],
    "market_impact": {{
        "short_term": "短期影响分析",
        "long_term": "长期影响分析"
    }},
    "key_points": ["要点1", "要点2", "要点3"],
    "recommendation": "投资建议"
}}

## 新闻内容
{news_text}
"""

# ============================================================
# 上市公司公告分析 Prompt
# ============================================================

ANNOUNCEMENT_ANALYSIS_PROMPT = """
请对以下上市公司公告进行专业分析，输出格式必须为 JSON，包含以下字段：

## 分析要求
1. **core_event**: 核心事件概述（一句话）
2. **event_type**: 事件类型（如：业绩预告、重大合同、股权变动、分红派息、资产重组、其他）
3. **financial_data**: 提取的财务数据
   - 如果有财务数据，提取关键指标
   - 如果没有，注明"未提及"
4. **impact_analysis**: 对公司的影响分析
   - 正面影响
   - 负面影响
5. **risks**: 风险提示列表
6. **market_impact**: 对市场的影响
7. **investor_advice**: 投资者建议
8. **key_deadlines**: 关键时间节点（如有）

## 输出格式
请严格按以下 JSON 格式输出，不要包含其他内容：
{{
    "core_event": "核心事件概述",
    "event_type": "事件类型",
    "financial_data": {{
        "revenue": "营业收入（或未提及）",
        "net_profit": "净利润（或未提及）",
        "growth_rate": "增长率（或未提及）",
        "other_metrics": "其他关键指标（或未提及）"
    }},
    "impact_analysis": {{
        "positive": ["正面影响1", "正面影响2"],
        "negative": ["负面影响1", "负面影响2"]
    }},
    "risks": ["风险1", "风险2"],
    "market_impact": "对市场的影响分析",
    "investor_advice": "投资者建议",
    "key_deadlines": ["时间节点1", "时间节点2"]
}}

## 公告内容
{announcement_text}
"""

# ============================================================
# 市场热点分析 Prompt
# ============================================================

HOTSPOT_ANALYSIS_PROMPT = """
请对以下多条财经新闻进行市场热点分析，输出格式必须为 JSON，包含以下字段：

## 分析要求
1. **hot_topics**: 当前最热的 3-5 个话题，按热度排序
2. **keywords**: 高频关键词列表（含出现频率）
3. **hot_industries**: 热门行业分析
4. **hot_companies**: 被频繁提及的公司
5. **market_sentiment**: 整体市场情绪分析
6. **trend_analysis**: 趋势判断
7. **attention_areas**: 值得关注的领域

## 输出格式
请严格按以下 JSON 格式输出，不要包含其他内容：
{{
    "hot_topics": [
        {{"topic": "话题1", "heat": "热度描述", "description": "简要说明"}},
        {{"topic": "话题2", "heat": "热度描述", "description": "简要说明"}}
    ],
    "keywords": [
        {{"word": "关键词1", "frequency": "高/中/低", "context": "出现的上下文"}},
        {{"word": "关键词2", "frequency": "高/中/低", "context": "出现的上下文"}}
    ],
    "hot_industries": [
        {{"industry": "行业1", "heat_index": 85, "reason": "热门原因"}},
        {{"industry": "行业2", "heat_index": 70, "reason": "热门原因"}}
    ],
    "hot_companies": [
        {{"company": "公司1", "mention_count": 5, "reason": "被关注原因"}}
    ],
    "market_sentiment": {{
        "overall": "整体情绪描述",
        "bullish_factors": ["看多因素1", "看多因素2"],
        "bearish_factors": ["看空因素1", "看空因素2"]
    }},
    "trend_analysis": "趋势判断分析",
    "attention_areas": ["领域1", "领域2", "领域3"]
}}

## 新闻列表
{news_list}
"""

# ============================================================
# 股票深度解码分析 Prompt
# ============================================================

STOCK_DEEP_DECODE_PROMPT = """
你是一位拥有 CFA（特许金融分析师）资格、并在顶级头部券商工作多年的资深量化策略师兼行业研究员。
你精通 A股（主板/科创板/创业板/北交所）、港股、美股的编码规则、上市制度、监管特征、交易机制及行为金融学。

用户提供了一个股票代码（或股票名称）：【 {user_stock_input} 】。

请严格按照以下四个步骤进行分步推理，输出一份结构严密的多维度深度解码报告。
输出格式必须为 JSON，包含以下完整结构：

{{
    "part1_market_identity": {{
        "market_judgment": {{
            "market": "所属市场（A股沪市主板/深市主板/创业板/科创板/北交所/港股/美股等）",
            "reason": "判断依据（代码数字/字母特征分析）",
            "exchange": "所属交易所全称",
            "regulator": "监管机构全称",
            "stock_name": "对应的上市公司名称（如可推断）",
            "business_sector": "主营业务板块"
        }},
        "trading_rules": {{
            "settlement": "T+0 或 T+1",
            "price_limit": "涨跌幅限制说明（如：主板±10%，创业板±20%等）",
            "short_selling": "是否允许融券做空"
        }},
        "abnormal_thresholds": {{
            "rule_description": "异动公告触发条件详细说明",
            "a_share_mainboard": "A股主板：连续3个交易日内日收盘价格涨跌幅偏离值累计达到±20%",
            "chi_next": "创业板：连续3个交易日内日收盘价格涨跌幅偏离值累计达到±30%",
            "other_rules": "其他板块特殊规则"
        }}
    }},
    "part2_price_action": {{
        "abnormal_assessment": "该股票近期市场环境下的整体表现评估",
        "capital_flow_analysis": "从资金面推演可能的微观交易行为（游资/机构/北向资金等）",
        "intraday_anomaly": "盘中急涨急跌异动分析（如一分钟内涨跌幅±3%或±5%的含义）"
    }},
    "part3_drivers_sentiment": {{
        "driver_types": {{
            "fundamental": "基本面驱动因素分析",
            "policy": "政策周期驱动因素分析",
            "sentiment": "情绪题材驱动因素分析"
        }},
        "market_sentiment": {{
            "overall": "整体情绪倾向（极度贪婪/温和看多/多空分歧/恐慌退潮）",
            "risk_warning": "是否存在利好出尽或情绪过度透支风险"
        }}
    }},
    "part4_outlook_strategy": {{
        "technical_levels": {{
            "support": "心理支撑位分析",
            "resistance": "上行阻力位分析"
        }},
        "risk_reward_ratio": {{
            "upside_space": "向上博弈空间评估",
            "downside_space": "下行风险空间评估",
            "ratio": "风险收益比对比"
        }},
        "strategy_advice": {{
            "short_term": "短线趋势交易者策略建议",
            "mid_term": "中线价值投资者策略建议"
        }}
    }},
    "disclaimer": "以上分析基于历史公开数据与交易规则推演，不构成任何投资买卖建议。"
}}

## 分析要求
1. 拒绝模糊：严禁出现"根据具体情况而定"等废话。基于该股票的历史波动率和行业均值给出合理的区间预测和量化参考。
2. 格式强调：所有涉及规则、比例、百分比、核心支撑/阻力位的文本必须进行加粗显示。
3. 必须包含免责声明。

## 用户输入的股票代码/名称
{user_stock_input}
"""

# ============================================================
# 多股票对比分析 Prompt
# ============================================================

STOCK_COMPARISON_PROMPT = """
你是一位拥有 CFA 资格的资深量化策略师。请对以下多只股票进行横向对比分析。

## 分析要求
请严格按照以下 JSON 格式输出对比分析报告：

{{
    "comparison_table": [
        {{
            "stock_name": "股票名称",
            "stock_code": "股票代码",
            "market": "所属市场（A股主板/科创板/创业板/北交所/港股/美股）",
            "exchange": "交易所",
            "sector": "所属行业板块",
            "price_limit": "涨跌幅限制",
            "settlement": "结算方式（T+0/T+1）",
            "short_selling": "是否支持融券做空",
            "min_tick": "最小变动单位",
            "listing_requirements": "上市制度（核准制/注册制）",
            "regulator": "监管机构",
            "investor_threshold": "投资者门槛"
        }}
    ],
    "key_differences": [
        "关键差异点1：...",
        "关键差异点2：...",
        "关键差异点3：..."
    ],
    "cross_market_arbitrage": "跨市场套利机会分析（如适用）",
    "investment_strategy": "基于对比的投资策略建议",
    "risk_warnings": [
        "风险提示1",
        "风险提示2"
    ],
    "disclaimer": "免责声明"
}}

## 待分析股票
{user_stock_input}
"""

# ============================================================
# Prompt 管理类
# ============================================================

class PromptManager:
    """Prompt 管理器，集中管理所有提示词模板"""

    PROMPTS = {
        "news_analysis": {
            "name": "财经新闻分析",
            "template": NEWS_ANALYSIS_PROMPT,
            "description": "对单条财经新闻进行深度分析",
        },
        "announcement_analysis": {
            "name": "公告分析",
            "template": ANNOUNCEMENT_ANALYSIS_PROMPT,
            "description": "对上市公司公告进行专业分析",
        },
        "hotspot_analysis": {
            "name": "市场热点分析",
            "template": HOTSPOT_ANALYSIS_PROMPT,
            "description": "从多条新闻中提取市场热点",
        },
        "stock_deep_decode": {
            "name": "股票深度解码",
            "template": STOCK_DEEP_DECODE_PROMPT,
            "description": "对股票代码进行多维度深度解码分析（市场归属、异动规则、资金行为、策略建议）",
        },
        "stock_comparison": {
            "name": "多股票对比分析",
            "template": STOCK_COMPARISON_PROMPT,
            "description": "对多只股票进行横向对比分析（市场归属、交易规则、估值、策略）",
        },
    }

    @classmethod
    def get_prompt(cls, name: str) -> str:
        """获取指定名称的 Prompt 模板"""
        prompt_info = cls.PROMPTS.get(name)
        if not prompt_info:
            raise ValueError(f"未找到名为 '{name}' 的 Prompt 模板")
        return prompt_info["template"]

    @classmethod
    def get_all_prompts(cls) -> dict:
        """获取所有 Prompt 模板信息"""
        return cls.PROMPTS

    @classmethod
    def add_prompt(cls, name: str, template: str, description: str = ""):
        """添加新的 Prompt 模板（支持扩展）"""
        cls.PROMPTS[name] = {
            "name": name,
            "template": template,
            "description": description,
        }
