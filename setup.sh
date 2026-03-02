#!/bin/bash
# 内涵质控系统 - 环境设置脚本（Linux/Mac）

echo "========================================"
echo "内涵质控系统 - 环境设置"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

echo "[1/4] 检查Python版本..."
python3 --version

# 创建虚拟环境
echo
echo "[2/4] 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境并安装依赖
echo
echo "[3/4] 安装依赖包..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 测试连接
echo
echo "[4/4] 测试ModelScope连接..."
python test_modelscope.py

echo
echo "========================================"
echo "环境设置完成！"
echo "========================================"
echo
echo "使用方法："
echo "  1. 激活虚拟环境: source venv/bin/activate"
echo "  2. 启动Web界面: python web_ui.py"
echo "  3. 启动命令行: python cli.py"
echo "  4. 启动API服务: python start.py"
echo
