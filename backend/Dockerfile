# 后端镜像：Python 3.11 slim + FastAPI
FROM python:3.11-slim

# 清除 Docker Desktop 自动注入的代理环境变量（WSL 内 127.0.0.1:7897 不通）
# pip/apt 走国内镜像源，无需代理
ENV HTTP_PROXY="" \
    HTTPS_PROXY="" \
    http_proxy="" \
    https_proxy="" \
    NO_PROXY="*" \
    no_proxy="*"

# 系统依赖：pypdf / Pillow 需要 libjpeg；pdf2image 需要 poppler（OCR 可选，缺省自动降级）
# 若构建环境无外网代理，apt-get 会失败，此处改为容错模式：
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= \
    apt-get update -o Acquire::http::Timeout=5 \
        -o Acquire::https::Timeout=5 \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    || (echo "WARNING: apt-get failed, skipping system packages (JPEG/PDF may be degraded)" && true)

WORKDIR /app

# 先装依赖，利用层缓存
COPY requirements.txt .
RUN HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= \
    pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 复制后端代码
COPY app ./app
COPY run.py .

# SQLite 数据与用户上传文件持久化到卷
VOLUME ["/app/data"]

# 生产环境关闭 reload；端口可被环境变量覆盖
ENV DEBUG=False
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
