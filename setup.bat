@echo off
REM 内涵质控系统 - 环境设置脚本（Windows）

echo ========================================
echo 内涵质控系统 - 环境设置
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 检查Python版本...
python --version

REM 创建虚拟环境
echo.
echo [2/4] 创建虚拟环境...
if exist venv (
    echo 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    echo 虚拟环境创建成功
)

REM 激活虚拟环境并安装依赖
echo.
echo [3/4] 安装依赖包...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 测试连接
echo.
echo [4/4] 测试ModelScope连接...
python test_modelscope.py

echo.
echo ========================================
echo 环境设置完成！
echo ========================================
echo.
echo 使用方法：
echo   1. 激活虚拟环境: venv\Scripts\activate.bat
echo   2. 启动Web界面: python web_ui.py
echo   3. 启动命令行: python cli.py
echo   4. 启动API服务: python start.py
echo.
pause
