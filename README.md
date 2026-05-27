# 📈 AI 金融信息分析助手

> **AI Financial Insight Assistant** — 智能分析财经新闻，洞见金融市场趋势

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 项目简介

**AI 金融信息分析助手** 是一款基于大模型 API 的智能金融信息分析工具。它利用 AI 技术对财经新闻、上市公司公告进行自动分析，帮助用户快速理解市场动态，解决金融信息过载问题。

### 核心功能

| 功能模块 | 说明 |
|---------|------|
| 📰 **财经新闻分析** | 自动输出三句话总结、利好/利空判断、涉及行业/公司、风险提示、市场影响 |
| 📋 **上市公司公告分析** | 提取核心事件、财务数据、风险提示、市场影响、投资者建议 |
| 🔥 **市场热点分析** | 提取高频关键词、热门行业、热门公司、市场情绪分析 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个有效的 API Key（支持 DeepSeek 或 OpenAI）

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/yourusername/AI-Financial-Insight-Assistant.git
cd AI-Financial-Insight-Assistant
```

2. **创建虚拟环境（推荐）**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置 API Key**

**方式一：环境变量（推荐）**

```bash
# Windows (CMD)
set DEEPSEEK_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your_api_key_here"

# macOS/Linux
export DEEPSEEK_API_KEY=your_api_key_here
```

**方式二：创建 `.env` 文件**

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
# 或
OPENAI_API_KEY=your_api_key_here
```

**方式三：页面输入**

启动后在页面侧边栏手动输入 API Key。

5. **启动应用**

```bash
streamlit run app.py
```

6. **打开浏览器**

访问终端显示的地址（通常是 `http://localhost:8501`）

---

## 🏗️ 项目结构

```
AI-Financial-Insight-Assistant/
│
├── app.py                  # 主入口 - Streamlit 多页面应用
├── requirements.txt        # Python 依赖清单
├── README.md               # 项目说明文档
│
├── services/               # API 服务层
│   ├── __init__.py
│   └── api_client.py       # API 客户端封装（支持 DeepSeek/OpenAI）
│
├── prompts/                # Prompt 模板管理
│   ├── __init__.py
│   └── financial_prompts.py # 金融分析专用 Prompt 模板
│
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── config.py           # 应用配置
│   └── helpers.py          # 辅助函数（JSON解析、缓存、格式化）
│
└── data/                   # 数据目录（用于后续扩展）
```

### 模块说明

| 模块 | 职责 | 扩展方向 |
|------|------|---------|
| `services/` | API 调用封装，支持多后端切换 | 可扩展为 Agent 调用、RAG 检索增强 |
| `prompts/` | Prompt 模板集中管理 | 可添加更多分析模板、支持 i18n |
| `utils/` | 通用工具函数 | 可添加数据持久化、日志等功能 |
| `data/` | 数据存储目录 | 可用于缓存、历史记录持久化 |

---

## 🎨 功能展示

### 1. 财经新闻分析

输入任意财经新闻，AI 自动输出：

- ✅ **三句话总结** — 快速把握新闻核心
- 📊 **利好/利空判断** — 附带置信度和判断依据
- 🏭 **涉及行业** — 自动识别相关行业
- 🏢 **涉及公司** — 自动识别相关公司
- ⚠️ **风险提示** — 专业风险分析
- 📈 **市场影响** — 短期和长期影响分析
- 💡 **投资建议** — 谨慎/关注/观望/回避

### 2. 上市公司公告分析

输入公告内容，AI 自动提取：

- 🎯 **核心事件** — 一句话概括
- 💰 **财务数据** — 营业收入、净利润、增长率等
- 📊 **影响分析** — 正面/负面影响
- ⚠️ **风险提示** — 潜在风险
- 💡 **投资者建议** — 专业建议
- 📅 **关键时间节点** — 重要日期

### 3. 市场热点分析

输入多条新闻，AI 自动提取：

- 🔥 **热门话题** — 按热度排序
- 🔑 **高频关键词** — 含出现频率
- 🏭 **热门行业** — 热度指数评分
- 🏢 **热门公司** — 被提及次数
- 📊 **市场情绪** — 看多/看空因素
- 🔮 **趋势判断** — 市场趋势分析

---

## ⚙️ 技术特性

- **模块化架构** — 各功能模块独立，便于维护和扩展
- **多后端支持** — 支持 DeepSeek、OpenAI 等多种 API 后端
- **Prompt 集中管理** — 所有提示词模板统一管理，便于优化
- **完善的错误处理** — 网络重试、JSON 解析容错、友好错误提示
- **金融科技风格 UI** — 深色主题、现代化设计、流畅交互
- **会话历史** — 本次会话的分析记录可回溯查看
- **缓存机制** — 内置简单缓存，减少重复请求

---

## 🔧 配置说明

### API 后端支持

| 后端 | 环境变量 | 默认模型 |
|------|---------|---------|
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |

### 页面配置

所有配置在 [`utils/config.py`](utils/config.py) 中管理，包括：

- 应用标题、图标
- 主题颜色
- 功能模块开关
- API 默认参数

---

## 🔮 后续扩展计划

- [ ] **Agent 模式** — 支持多轮对话和自主分析
- [ ] **RAG 检索增强** — 接入知识库，提供更精准的分析
- [ ] **数据持久化** — 保存分析记录到数据库
- [ ] **批量分析** — 支持批量导入新闻进行分析
- [ ] **图表可视化** — 集成 Plotly 图表展示趋势
- [ ] **多语言支持** — 支持英文等其他语言
- [ ] **定时监控** — 定时抓取新闻并自动分析
- [ ] **WebSocket 实时推送** — 实时市场动态监控

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## ⚠️ 免责声明

本工具提供的分析内容仅供参考和学习研究使用，**不构成任何投资建议**。金融市场有风险，投资决策需谨慎。作者不对因使用本工具而产生的任何损失承担责任。

---

## 📄 许可证

本项目基于 MIT 许可证开源 — 详见 [LICENSE](LICENSE) 文件。

---

## 👨‍💻 作者

**AI Financial Insight Assistant** — 由 AI 全栈工程师开发

[![GitHub](https://img.shields.io/badge/GitHub-Profile-181717?logo=github)](https://github.com/yourusername)

---

*如果这个项目对你有帮助，请给一个 ⭐️ 支持！*
