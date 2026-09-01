@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  业务数据清洗与未回销看板 — Windows 一键启动脚本
::  双击即可运行，无需手动配置
:: ============================================================

title 业务数据清洗与未回销看板

echo.
echo ================================================
echo   业务数据清洗与未回销看板
echo   正在初始化，请稍候...
echo ================================================
echo.

:: ---- 1. 检测路径是否含中文 ----
set "CURRENT_DIR=%~dp0"
echo !CURRENT_DIR! | findstr /i "[^\x00-\x7F]" >nul
if not errorlevel 1 (
    echo [警告] 当前目录路径包含中文字符，可能导致 Python 运行异常
    echo [建议] 请将项目文件夹移动到纯英文路径下（如 C:\Projects\dashboard）
    echo.
    choice /C YN /M "是否仍要继续运行？"
    if errorlevel 2 exit /b 1
)

:: ---- 2. 检测 Python ----
echo [1/4] 检测 Python 环境...

:: 尝试 python3，再尝试 python
set "PYTHON_CMD="
for %%p in (python3 python) do (
    where %%p >nul 2>&1
    if not errorlevel 1 (
        %%p --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=%%p"
        if defined PYTHON_CMD goto :py_found
    )
)

:py_not_found
echo.
echo [错误] 未检测到 Python！
echo [解决] 请先安装 Python 3.10 或更高版本：
echo        https://www.python.org/downloads/
echo        安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:py_found
for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo        ✓ 已检测到 Python %PY_VER% (%PYTHON_CMD%)

:: 检查版本 >= 3.10
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
)
if !MAJOR! LSS 3 (
    echo [错误] Python 版本过低，需要 3.10 或更高版本
    pause
    exit /b 1
)
if !MAJOR! EQU 3 if !MINOR! LSS 10 (
    echo [错误] Python 版本过低 ^(!PY_VER!^)，需要 3.10 或更高版本
    pause
    exit /b 1
)
echo        ✓ 版本检查通过
echo.

:: ---- 3. 创建/激活虚拟环境 ----
echo [2/4] 准备虚拟环境...
set "VENV_DIR=%~dp0venv"

if not exist "!VENV_DIR!\Scripts\python.exe" (
    echo        正在创建虚拟环境...
    %PYTHON_CMD% -m venv "!VENV_DIR!" 2>&1
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败，请确认 Python 安装完整
        pause
        exit /b 1
    )
    echo        ✓ 虚拟环境已创建
) else (
    echo        ✓ 虚拟环境已存在
)

set "PIP_CMD=!VENV_DIR!\Scripts\python.exe -m pip"
echo.

:: ---- 4. 安装依赖 ----
echo [3/4] 安装依赖包...

!PIP_CMD! install -r "%~dp0requirements.txt" -q --disable-pip-version-check 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 依赖包安装失败，常见原因：
    echo        1. 公司网络限制 — 请连接外网后重试
    echo        2. 杀毒软件拦截 — 请暂时关闭实时防护
    echo        3. pip 源连接超时 — 请尝试切换网络
    echo.
    pause
    exit /b 1
)
echo        ✓ 依赖包安装完成
echo.

:: ---- 5. 启动看板 ----
echo [4/4] 启动数据看板...
echo.

:: 自动打开浏览器
start "" http://localhost:8501
if errorlevel 1 (
    echo [提示] 无法自动打开浏览器，请手动访问 http://localhost:8501
)

echo ================================================
echo   启动成功，请查看浏览器中的看板页面
echo   关闭此窗口即可停止服务
echo ================================================
echo.

:: 启动 Streamlit，终端保持可见
"!VENV_DIR!\Scripts\python.exe" -m streamlit run "%~dp0app.py" --server.headless false

:: 暂停以显示可能的错误信息
pause
