#!/bin/bash
# MindLink 启动脚本

cd /root/MindLink

# 激活虚拟环境
source venv/bin/activate

# 启动服务
exec gunicorn api.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:7003 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output
