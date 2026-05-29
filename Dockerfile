# ============================================================
# Dockerfile — AI Financial Insight Assistant
# ============================================================
# 基于 Python 3.11 slim 镜像，优化构建缓存与运行效率
# ============================================================

FROM python:3.11-slim

# ── 环境变量 ──────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ── 系统依赖 ──────────────────────────────────────────────
# AKShare 底层依赖：libgomp（OpenMP 并行计算支持）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ──────────────────────────────────────────────
WORKDIR /app

# ── 依赖安装（利用 Docker 层缓存） ────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 项目代码 ──────────────────────────────────────────────
COPY . .

# ── 健康检查 ──────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# ── 启动命令 ──────────────────────────────────────────────
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
