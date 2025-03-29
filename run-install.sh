#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

printf "\033]0;Applio使用UV安装\007"
clear
# rm -f *.bat # Keep this? Maybe not necessary if user clones fresh. Let's remove it for now.

# Function to log messages with timestamps
log_message() {
    local msg="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $msg"
}

# Function to find a suitable Python version (prefer python3.10+)
find_python() {
    for py_cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$py_cmd" > /dev/null 2>&1; then
            version_str=$("$py_cmd" --version 2>&1)
            if [[ "$version_str" == *"Python 3."* ]]; then
                py_major=$(echo "$version_str" | sed -n 's/Python \([0-9]*\)\..*/\1/p')
                py_minor=$(echo "$version_str" | sed -n 's/Python [0-9]*\.\([0-9]*\)\..*/\1/p')
                if [ "$py_major" -eq 3 ] && [ "$py_minor" -ge 10 ]; then
                    echo "$py_cmd"
                    return 0
                fi
            fi
        fi
    done
    log_message "No compatible Python installation found (Python 3.10+ required). Please install Python 3.10 or newer."
    return 1
}

# Function to check if UV is installed
check_uv() {
    log_message "检查UV是否已安装..."
    
    # 检查系统路径
    if command -v uv > /dev/null 2>&1; then
        log_message "UV已安装在系统路径中"
        UV_CMD="uv"
        return 0
    fi
    
    # 检查Python模块
    if "$PYTHON_CMD" -m uv --version > /dev/null 2>&1; then
        log_message "UV已通过Python模块安装"
        UV_CMD="$PYTHON_CMD -m uv"
        return 0
    fi
    
    # UV未安装，提供安装选项
    echo "UV未安装。请选择安装方式："
    echo "1. 使用独立安装程序（推荐）"
    echo "2. 使用pip安装"
    echo "3. 使用Homebrew安装（仅macOS）"
    echo "4. 使用Cargo安装（需要Rust工具链）"
    echo "5. 手动安装（取消）"
    printf "请输入选择编号: "
    read -r install_choice
    
    case "$install_choice" in
        1)
            log_message "使用独立安装程序安装UV..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            if [ $? -eq 0 ]; then
                log_message "UV安装成功！"
                UV_CMD="uv"
                return 0
            fi
            ;;
        2)
            log_message "使用pip安装UV..."
            "$PYTHON_CMD" -m pip install uv
            if [ $? -eq 0 ]; then
                log_message "UV安装成功！"
                UV_CMD="$PYTHON_CMD -m uv"
                return 0
            fi
            ;;
        3)
            if command -v brew > /dev/null 2>&1; then
                log_message "使用Homebrew安装UV..."
                brew install uv
                if [ $? -eq 0 ]; then
                    log_message "UV安装成功！"
                    UV_CMD="uv"
                    return 0
                fi
            else
                log_message "Homebrew未安装，无法使用此方法"
            fi
            ;;
        4)
            if command -v cargo > /dev/null 2>&1; then
                log_message "使用Cargo安装UV..."
                cargo install --git https://github.com/astral-sh/uv uv
                if [ $? -eq 0 ]; then
                    log_message "UV安装成功！"
                    UV_CMD="uv"
                    return 0
                fi
            else
                log_message "Cargo未安装，无法使用此方法"
            fi
            ;;
        *)
            log_message "取消安装。"
            return 1
            ;;
    esac
    
    log_message "UV安装失败，请参考 https://docs.astral.sh/uv/getting-started/installation/ 手动安装。"
    return 1
}

# Function to select PyTorch backend
select_backend() {
    echo "Please select the PyTorch backend to install:"
    echo "1. cpu (CPU only)"
    echo "2. cu118 (CUDA 11.8)"
    echo "3. cu121 (CUDA 12.1)"
    echo "4. cu124 (CUDA 12.4)"
    echo "5. rocm (ROCm - Experimental)"
    echo "6. xpu (Intel GPU - Experimental)"
    printf "Enter the number of your choice (e.g., 3 for cu121): "
    read -r backend_choice

    case "$backend_choice" in
        1) PYTORCH_EXTRA="cpu" ;;
        2) PYTORCH_EXTRA="cu118" ;;
        3) PYTORCH_EXTRA="cu121" ;;
        4) PYTORCH_EXTRA="cu124" ;;
        5) PYTORCH_EXTRA="rocm" ;;
        6) PYTORCH_EXTRA="xpu" ;;
        *)
            log_message "Invalid choice. Please run the script again."
            return 1
            ;;
    esac
    log_message "Selected backend: $PYTORCH_EXTRA"
    echo ""
    return 0
}

# Function to create UV environment
create_uv_env() {
    log_message "Creating virtual environment using UV..."
    if ! "$PYTHON_CMD" -m uv venv .venv --python "$PYTHON_CMD"; then
        log_message "Failed to create virtual environment using UV."
        return 1
    fi
    log_message "Virtual environment created successfully at .venv"
    echo ""
    return 0
}

# Function to install dependencies using UV
install_dependencies() {
    log_message "Installing dependencies for backend '$PYTORCH_EXTRA' using UV..."
    log_message "This might take a while depending on your internet connection and system specs."
    # Activate venv temporarily for the command or use absolute path to uv
    if ! .venv/bin/uv sync --extra "$PYTORCH_EXTRA"; then
        log_message "Failed to install dependencies using UV sync."
        return 1
    fi
    log_message "Dependencies installation complete."
    echo ""
    return 0
}

# --- Main Script Execution ---

# 1. Check for existing venv
if [ -d ".venv" ]; then
    log_message "发现已存在的.venv目录。"
    
    # 检查是否有Python进程正在使用该虚拟环境
    log_message "检查是否有Python进程正在使用该虚拟环境..."
    
    # 查找包含当前目录绝对路径的Python进程
    CURRENT_DIR=$(pwd)
    PYTHON_PROCESSES=$(ps aux | grep python | grep "$CURRENT_DIR/.venv" | grep -v grep)
    
    if [ -n "$PYTHON_PROCESSES" ]; then
        echo "检测到以下Python进程可能正在使用虚拟环境："
        echo "$PYTHON_PROCESSES"
        
        printf "是否要结束这些进程以安全删除虚拟环境？(Y/N): "
        read -r kill_processes
        kill_processes=$(echo "$kill_processes" | tr '[:upper:]' '[:lower:]')
        
        if [ "$kill_processes" = "y" ]; then
            if [ "$(id -u)" -ne 0 ]; then
                log_message "需要提权以结束这些进程..."
                echo "请输入您的密码以获取提权："
                
                # 提取进程ID并尝试使用sudo终止它们
                PROCESS_IDS=$(echo "$PYTHON_PROCESSES" | awk '{print $2}')
                for pid in $PROCESS_IDS; do
                    sudo kill -9 "$pid" || log_message "无法结束进程 $pid"
                done
            else
                # 已有root权限
                PROCESS_IDS=$(echo "$PYTHON_PROCESSES" | awk '{print $2}')
                for pid in $PROCESS_IDS; do
                    kill -9 "$pid" || log_message "无法结束进程 $pid"
                done
            fi
            log_message "已尝试结束所有相关Python进程。"
        else
            log_message "未结束Python进程，删除虚拟环境可能会失败。"
        fi
    fi
    
    printf "是否要删除现有环境并重新安装？(Y/N): "
    read -r r
    r=$(echo "$r" | tr '[:upper:]' '[:lower:]')
    if [ "$r" = "y" ]; then
        log_message "正在删除现有的.venv目录..."
        if ! rm -rf .venv; then
            log_message "删除现有.venv目录失败。请手动删除或确保没有程序正在使用它。"
            log_message "您可以尝试使用: sudo rm -rf .venv"
            exit 1
        fi
        log_message "现有.venv目录已删除。"
    else
        log_message "按照要求跳过安装。您可以尝试运行'./run-applio.sh'。"
        exit 0
    fi
fi

# 2. Find Python
PYTHON_CMD=$(find_python)
if [ $? -ne 0 ]; then
    exit 1
fi
log_message "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 3. Check/Install UV
check_uv
if [ $? -ne 0 ]; then
    exit 1
fi

# 4. Select Backend
select_backend
if [ $? -ne 0 ]; then
    exit 1
fi

# 5. Create Environment
create_uv_env
if [ $? -ne 0 ]; then
    exit 1
fi

# 6. Install Dependencies
install_dependencies
if [ $? -ne 0 ]; then
    exit 1
fi

# 7. Install FFmpeg (Still needed system-wide for ffmpeg-python?)
# Let's keep the FFmpeg install logic for now, as ffmpeg-python might need the binary.
# Consider making this optional or providing instructions if install fails.
log_message "Checking/Installing FFmpeg (required by ffmpeg-python)..."
if ! command -v ffmpeg > /dev/null; then
    log_message "FFmpeg not found. Attempting to install..."
    if command -v brew > /dev/null; then
        log_message "Installing FFmpeg using Homebrew on macOS..."
        brew install ffmpeg || log_message "Failed to install ffmpeg via brew."
    elif command -v apt-get > /dev/null; then
        log_message "Installing FFmpeg using apt..."
        sudo apt-get update && sudo apt-get install -y ffmpeg || log_message "Failed to install ffmpeg via apt."
    elif command -v pacman > /dev/null; then
        log_message "Installing FFmpeg using pacman..."
        sudo pacman -Syu --noconfirm ffmpeg || log_message "Failed to install ffmpeg via pacman."
    elif command -v dnf > /dev/null; then
        log_message "Installing FFmpeg using dnf..."
        sudo dnf install -y ffmpeg || log_message "Failed to install ffmpeg via dnf."
    else
        log_message "Could not detect package manager (apt, brew, pacman, dnf) to install FFmpeg automatically."
        log_message "Please install FFmpeg manually for your system."
    fi
else
    log_message "FFmpeg found."
fi

# 8. macOS Specifics (Keep faiss install for now, might be needed)
if [ "$(uname)" = "Darwin" ]; then
    log_message "Running macOS specific steps..."
    if command -v brew >/dev/null 2>&1; then
         if ! brew list faiss >/dev/null 2>&1; then
             log_message "Installing faiss using Homebrew..."
             brew install faiss || log_message "Failed to install faiss via brew."
         else
             log_message "faiss already installed via Homebrew."
         fi
    else
        log_message "Homebrew not found. Cannot install faiss automatically. Please install it if needed."
    fi
    # Environment variables moved to run-applio.sh
fi

# 9. Finish
clear
log_message "Applio installation using UV completed successfully."
echo "Run './run-applio.sh' to start the web interface!"
exit 0
