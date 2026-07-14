# 后端镜像：Python 3.11 slim + FastAPI
FROM python:3.11-slim

# 系统依赖：pypdf / Pillow 需要 libjpeg；pdf2image 需要 poppler（OCR 可选，缺省自动降级）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 优先用国内镜像源加速（无网络时删除此行即可）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 先装依赖，利用层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY app ./app
COPY run.py .

# SQLite 数据与用户上传文件持久化到卷
VOLUME ["/app/data"]

# 生产环境关闭 reload；端口可被环境变量覆盖
ENV DEBUG=False
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
