@echo off
:: 1. 切换到脚本所在的当前目录
cd /d "%~dp0"

:: 2. 检查 .venv 文件夹是否存在
if not exist ".venv" (
    echo [ERROR] Cannot find .venv folder! 
    echo Please make sure you are in the correct directory.
    pause
    exit /b
)

:: 3. 激活虚拟环境并运行 Streamlit
echo [INFO] Activating virtual environment and starting Streamlit...
call .venv\Scripts\activate.bat

:: 4. 运行你的程序
python -m streamlit run app.py

:: 如果程序意外关闭，保留窗口显示报错信息
pause