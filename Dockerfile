FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p password_manager/data

# 暴露端口
EXPOSE 5000

# 启动应用（绑定 0.0.0.0 以允许宿主机访问，但宿主机端口只绑定到 127.0.0.1）
CMD ["python", "-c", "from web_app import app, create_templates; create_templates(); app.run(host='0.0.0.0', port=5000, debug=False)"]