@echo off
chcp 65001 >nul
if not exist .venv (
    echo [1/3] 创建 Python 虚拟环境...
    python -m venv .venv
)
echo [2/3] 安装项目依赖...
call .venv\Scripts\activate
python -m pip install -r requirements.txt
echo [3/3] 启动 DataMind AI...
python -m streamlit run app.py

