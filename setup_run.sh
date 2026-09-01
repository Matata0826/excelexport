#!/usr/bin/env bash
# ============================================================
#  业务数据清洗与未回销看板 — macOS/Linux 一键启动脚本
#  用法: chmod +x setup_run.sh && ./setup_run.sh
# ============================================================

set -euo pipefail

# ---- 颜色定义 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  业务数据清洗与未回销看板${NC}"
echo -e "${CYAN}  正在初始化，请稍候...${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# ---- 获取脚本所在目录 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---- 1. 检测路径是否含中文 ----
echo -e "[1/4] 检测运行环境..."
if echo "$SCRIPT_DIR" | grep -qP '[\x{4e00}-\x{9fff}]' 2>/dev/null; then
    echo -e "${YELLOW}[警告] 当前目录路径包含中文字符，可能导致 Python 运行异常${NC}"
    echo -e "${YELLOW}[建议] 请将项目文件夹移动到纯英文路径下${NC}"
    echo ""
    read -r -p "是否仍要继续运行？(y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ---- 2. 检测 Python ----
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" --version &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo -e "${RED}[错误] 未检测到 Python！${NC}"
    echo -e "${RED}[解决] 请先安装 Python 3.10 或更高版本${NC}"
    echo -e "${RED}       macOS: brew install python@3.12${NC}"
    echo -e "${RED}       Ubuntu: sudo apt install python3${NC}"
    echo -e "${RED}       https://www.python.org/downloads/${NC}"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "按任意键退出..."
        read -r
    fi
    exit 1
fi

PY_VER=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
echo -e "       ${GREEN}✓${NC} 已检测到 Python $PY_VER ($PYTHON_CMD)"

# 检查版本 >= 3.10
MAJOR=$(echo "$PY_VER" | cut -d. -f1)
MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
    echo -e "${RED}[错误] Python 版本过低 ($PY_VER)，需要 3.10 或更高版本${NC}"
    exit 1
fi
echo -e "       ${GREEN}✓${NC} 版本检查通过"
echo ""

# ---- 3. 创建/激活虚拟环境 ----
echo -e "[2/4] 准备虚拟环境..."
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "       正在创建虚拟环境..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 虚拟环境创建失败${NC}"
        exit 1
    fi
    echo -e "       ${GREEN}✓${NC} 虚拟环境已创建"
else
    echo -e "       ${GREEN}✓${NC} 虚拟环境已存在"
fi

PIP_CMD="$VENV_DIR/bin/python -m pip"
echo ""

# ---- 4. 安装依赖 ----
echo -e "[3/4] 安装依赖包..."

$PIP_CMD install -r "$SCRIPT_DIR/requirements.txt" -q --disable-pip-version-check 2>&1
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[错误] 依赖包安装失败，常见原因：${NC}"
    echo -e "${RED}       1. 公司网络限制 — 请连接外网后重试${NC}"
    echo -e "${RED}       2. pip 源连接超时 — 请尝试切换网络${NC}"
    echo ""
    exit 1
fi
echo -e "       ${GREEN}✓${NC} 依赖包安装完成"
echo ""

# ---- 5. 启动看板 ----
echo -e "[4/4] 启动数据看板..."
echo ""

# 自动打开浏览器
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8501 2>/dev/null || true
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:8501 2>/dev/null || true
fi

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  启动成功，请查看浏览器中的看板页面${NC}"
echo -e "${CYAN}  按 Ctrl+C 即可停止服务${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# 启动 Streamlit
exec "$VENV_DIR/bin/python" -m streamlit run "$SCRIPT_DIR/app.py" --server.headless false
