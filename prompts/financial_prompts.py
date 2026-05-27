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
