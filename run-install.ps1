<#
.SYNOPSIS
    Applio 安装脚本 (PowerShell 版)
.DESCRIPTION
    使用 UV 安装和管理 Applio 虚拟环境
#>

# 设置中文编码环境
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 基本信息设置
$INSTALL_DIR = $PSScriptRoot
$VENV_DIR = Join-Path $INSTALL_DIR ".venv"
$PYTHON_EXE = Join-Path $VENV_DIR "Scripts\python.exe"
$UV_EXE = Join-Path $VENV_DIR "Scripts\uv.exe"

# 记录开始时间
$startTime = Get-Date

# 主安装流程
function Main {
    Write-Host "欢迎使用Applio安装程序！(使用UV)" -ForegroundColor Cyan
    Write-Host ""

    # 检查现有虚拟环境
    if (-not (CheckExistingVenv)) { exit 1 }

    # 检查/安装 UV
    if (-not (CheckUV)) { exit 1 }

    # 选择后端
    if (-not (SelectBackend)) { exit 1 }

    # 创建虚拟环境
    if (-not (CreateUVEnv)) { exit 1 }

    # 安装依赖
    if (-not (InstallDependencies)) { exit 1 }

    # 计算安装时间
    $elapsed = (Get-Date) - $startTime
    $hours = $elapsed.Hours
    $minutes = $elapsed.Minutes
    $seconds = $elapsed.Seconds

    Write-Host "安装用时: ${hours}小时, ${minutes}分钟, ${seconds}秒。" -ForegroundColor Green
    Write-Host ""
    Write-Host "Applio已使用UV成功安装！" -ForegroundColor Green
    Write-Host "请运行'run-applio.ps1'启动Applio。" -ForegroundColor Yellow
    Write-Host ""
    Pause
}

# 检查现有虚拟环境
function CheckExistingVenv {
    if (Test-Path $VENV_DIR) {
        Write-Host "发现已存在的.venv目录。" -ForegroundColor Yellow
        
        # 检查是否有Python进程正在使用该虚拟环境
        Write-Host "检查是否有Python进程正在使用该虚拟环境..."
        $venvProcesses = Get-Process python -ErrorAction SilentlyContinue | 
            Where-Object { $_.Path -like "*$VENV_DIR*" }
        
        if ($venvProcesses) {
            Write-Host "检测到$($venvProcesses.Count)个Python进程正在使用此虚拟环境。" -ForegroundColor Yellow
            $killChoice = Read-Host "是否要结束这些进程以安全删除虚拟环境？(Y/N)"
            
            if ($killChoice -eq "Y" -or $killChoice -eq "y") {
                Write-Host "正在结束相关Python进程..."
                try {
                    $venvProcesses | Stop-Process -Force
                    Start-Sleep -Seconds 2
                    Write-Host "已尝试结束相关Python进程。" -ForegroundColor Green
                } catch {
                    Write-Host "结束进程时出错: $_" -ForegroundColor Red
                }
            } else {
                Write-Host "未结束Python进程，删除虚拟环境可能会失败。" -ForegroundColor Yellow
            }
        }
        
        $choice = Read-Host "是否要删除现有环境并重新安装？(Y/N)"
        if ($choice -eq "Y" -or $choice -eq "y") {
            Write-Host "正在删除现有的.venv目录..."
            try {
                Remove-Item $VENV_DIR -Recurse -Force -ErrorAction Stop
                Write-Host "现有.venv目录已删除。" -ForegroundColor Green
                return $true
            } catch {
                Write-Host "删除现有.venv目录失败。" -ForegroundColor Red
                Write-Host "这可能是因为：" -ForegroundColor Yellow
                Write-Host "1. 某些文件仍被程序占用" -ForegroundColor Yellow
                Write-Host "2. 需要管理员权限" -ForegroundColor Yellow
                Write-Host "请关闭所有相关程序后手动删除，或使用管理员权限运行此脚本。" -ForegroundColor Yellow
                Pause
                return $false
            }
        } else {
            Write-Host "按照要求跳过安装。您可以尝试运行'run-applio.ps1'。" -ForegroundColor Yellow
            Pause
            exit 0
        }
    }
    return $true
}

# 检查/安装 UV
function CheckUV {
    Write-Host "检查UV是否已安装..." -ForegroundColor Cyan
    
    # 检查系统路径
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "UV已安装在系统PATH中" -ForegroundColor Green
        $script:UV_CMD = "uv"
        return $true
    }
    
    # 检查Python模块
    try {
        $null = python -m uv --version 2>$null
        Write-Host "UV已通过Python模块安装" -ForegroundColor Green
        $script:UV_CMD = "python -m uv"
        return $true
    } catch {
        # UV未安装，提供安装选项
        Write-Host "UV未安装。请选择安装方式：" -ForegroundColor Yellow
        Write-Host "1. 使用独立安装程序（推荐）"
        Write-Host "2. 使用pip安装"
        Write-Host "3. 使用WinGet安装（需要Windows包管理器）"
        Write-Host "4. 使用Scoop安装（需要Scoop）"
        Write-Host "5. 手动安装（取消）"
        $installChoice = Read-Host "请输入选择编号"
        
        switch ($installChoice) {
            1 {
                Write-Host "使用独立安装程序安装UV..." -ForegroundColor Cyan
                try {
                    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
                    if (Get-Command uv -ErrorAction SilentlyContinue) {
                        Write-Host "UV安装成功！" -ForegroundColor Green
                        $script:UV_CMD = "uv"
                        return $true
                    }
                } catch {
                    Write-Host "独立安装程序执行失败: $_" -ForegroundColor Red
                }
            }
            2 {
                Write-Host "使用pip安装UV..." -ForegroundColor Cyan
                try {
                    pip install uv
                    if (python -m uv --version 2>$null) {
                        Write-Host "UV安装成功！" -ForegroundColor Green
                        $script:UV_CMD = "python -m uv"
                        return $true
                    }
                } catch {
                    Write-Host "pip安装失败: $_" -ForegroundColor Red
                }
            }
            3 {
                Write-Host "使用WinGet安装UV..." -ForegroundColor Cyan
                try {
                    winget install --id=astral-sh.uv -e
                    if (Get-Command uv -ErrorAction SilentlyContinue) {
                        Write-Host "UV安装成功！" -ForegroundColor Green
                        $script:UV_CMD = "uv"
                        return $true
                    }
                } catch {
                    Write-Host "WinGet安装失败: $_" -ForegroundColor Red
                }
            }
            4 {
                Write-Host "使用Scoop安装UV..." -ForegroundColor Cyan
                try {
                    scoop install main/uv
                    if (Get-Command uv -ErrorAction SilentlyContinue) {
                        Write-Host "UV安装成功！" -ForegroundColor Green
                        $script:UV_CMD = "uv"
                        return $true
                    }
                } catch {
                    Write-Host "Scoop安装失败: $_" -ForegroundColor Red
                }
            }
            default {
                Write-Host "取消安装。" -ForegroundColor Yellow
                return $false
            }
        }
        
        Write-Host "UV安装失败，请参考 https://docs.astral.sh/uv/getting-started/installation/ 手动安装。" -ForegroundColor Red
        return $false
    }
}

# 选择后端
function SelectBackend {
    Write-Host "请选择要安装的PyTorch后端：" -ForegroundColor Cyan
    Write-Host "1. cpu（仅CPU）"
    Write-Host "2. cu118（CUDA 11.8）"
    Write-Host "3. cu121（CUDA 12.1）"
    Write-Host "4. cu124（CUDA 12.4）"
    Write-Host "5. rocm（ROCm - 实验性）"
    Write-Host "6. xpu（Intel GPU - 实验性）"
    $backendChoice = Read-Host "请输入您的选择编号（例如，3表示cu121）"
    
    switch ($backendChoice) {
        1 { $script:PYTORCH_EXTRA = "cpu" }
        2 { $script:PYTORCH_EXTRA = "cu118" }
        3 { $script:PYTORCH_EXTRA = "cu121" }
        4 { $script:PYTORCH_EXTRA = "cu124" }
        5 { $script:PYTORCH_EXTRA = "rocm" }
        6 { $script:PYTORCH_EXTRA = "xpu" }
        default {
            Write-Host "无效选择。请重新运行脚本。" -ForegroundColor Red
            return $false
        }
    }
    
    Write-Host "已选择后端: $PYTORCH_EXTRA" -ForegroundColor Green
    Write-Host ""
    return $true
}

# 创建虚拟环境
function CreateUVEnv {
    Write-Host "正在使用UV创建虚拟环境..." -ForegroundColor Cyan
    try {
        Invoke-Expression "$UV_CMD venv `"$VENV_DIR`" --python 3.10"
        if (-not (Test-Path $PYTHON_EXE)) {
            throw "虚拟环境创建失败"
        }
        Write-Host "虚拟环境已成功创建于 $VENV_DIR" -ForegroundColor Green
        Write-Host ""
        return $true
    } catch {
        Write-Host "使用UV创建虚拟环境失败。" -ForegroundColor Red
        Write-Host "请检查Python 3.10是否已安装，或尝试手动创建虚拟环境。" -ForegroundColor Yellow
        return $false
    }
}

# 安装依赖函数 - 使用 uv pip install
function InstallDependencies {
    Write-Host "正在安装基础依赖..." -ForegroundColor Cyan
    $logFileBase = Join-Path $INSTALL_DIR "uv_pip_base_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    try {
        # 安装 pyproject.toml 中 [project].dependencies 定义的基础包
        Invoke-Expression "$UV_CMD pip install . --verbose *>&1 | Out-File -Encoding utf8 -FilePath $logFileBase"
        if ($LASTEXITCODE -ne 0) {
            throw "基础依赖安装失败 (uv pip install .)，退出代码: $LASTEXITCODE. 请检查日志: $logFileBase"
        }
        Write-Host "基础依赖安装完成。" -ForegroundColor Green
        Write-Host "详细日志: $logFileBase" -ForegroundColor DarkGray
    } catch {
        Write-Host "`n基础依赖安装失败。" -ForegroundColor Red
        Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "详细日志已保存到: $logFileBase" -ForegroundColor Yellow
        return $false
    }

    Write-Host "`n正在为后端 '$PYTORCH_EXTRA' 安装特定依赖..." -ForegroundColor Cyan
    Write-Host "根据您的网络连接和系统配置，这可能需要一些时间。" -ForegroundColor Yellow
    $logFileBackend = Join-Path $INSTALL_DIR "uv_pip_backend_${PYTORCH_EXTRA}_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    # 定义后端特定的包和索引URL
    $torchPackages = "torch>=2.3.1 torchvision>=0.18.1 torchaudio>=2.3.1"
    $indexUrl = ""
    $faissPackage = ""

    switch ($PYTORCH_EXTRA) {
        "cpu"   { $indexUrl = "https://download.pytorch.org/whl/cpu"; $faissPackage = "" } # faiss-cpu is base
        "cu118" { 
            $indexUrl = "https://download.pytorch.org/whl/cu118"
            if ($IsLinux) { $faissPackage = "faiss-gpu-cu11>=1.7.3" } 
            else { Write-Host "注意：faiss-gpu-cu11 仅在 Linux 上可用，此系统将跳过安装。" -ForegroundColor Yellow }
        }
        "cu121" { 
            $indexUrl = "https://download.pytorch.org/whl/cu121"
            if ($IsLinux) { $faissPackage = "faiss-gpu-cu12>=1.7.3" }
            else { Write-Host "注意：faiss-gpu-cu12 仅在 Linux 上可用，此系统将跳过安装。" -ForegroundColor Yellow }
        }
        "cu124" { 
            $indexUrl = "https://download.pytorch.org/whl/cu124"
            if ($IsLinux) { $faissPackage = "faiss-gpu-cu12>=1.7.3" }
            else { Write-Host "注意：faiss-gpu-cu12 仅在 Linux 上可用，此系统将跳过安装。" -ForegroundColor Yellow }
        }
        "rocm"  { 
            $indexUrl = "https://download.pytorch.org/whl/rocm6.0"
            # Faiss for ROCm TBD - Add check if package becomes available
            Write-Host "注意：ROCm 后端的 Faiss GPU 支持尚不明确，将跳过安装。" -ForegroundColor Yellow
            $faissPackage = "" 
        } 
        "xpu"   { 
            $indexUrl = "https://download.pytorch.org/whl/xpu"
             # Faiss for XPU TBD - Add check if package becomes available
            Write-Host "注意：XPU 后端的 Faiss GPU 支持尚不明确，将跳过安装。" -ForegroundColor Yellow
            $faissPackage = "" 
        }   
        default { Write-Host "未知的后端 '$PYTORCH_EXTRA'" -ForegroundColor Red; return $false }
    }

    # 构建安装命令
    $installCommand = "$UV_CMD pip install $torchPackages"
    if ($faissPackage) {
        $installCommand += " $faissPackage"
    }
    $installCommand += " --index-url $indexUrl --verbose *>&1 | Out-File -Encoding utf8 -FilePath $logFileBackend"

    Write-Host "将要执行: $installCommand" -ForegroundColor DarkGray # Log the command

    try {
        Invoke-Expression $installCommand
        if ($LASTEXITCODE -ne 0) {
            throw "后端 '$PYTORCH_EXTRA' 依赖安装失败 (uv pip install)，退出代码: $LASTEXITCODE. 请检查日志: $logFileBackend"
        }
        Write-Host "后端 '$PYTORCH_EXTRA' 特定依赖安装完成。" -ForegroundColor Green
        Write-Host "详细日志: $logFileBackend" -ForegroundColor DarkGray
        Write-Host ""
        return $true
    } catch {
        Write-Host "`n后端 '$PYTORCH_EXTRA' 特定依赖安装失败。" -ForegroundColor Red
        Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "详细日志已保存到: $logFileBackend" -ForegroundColor Yellow
        Write-Host "请检查日志文件以获取完整的错误输出和详细信息。" -ForegroundColor Yellow
        Write-Host "常见问题可能包括网络问题、索引URL错误或包版本冲突。" -ForegroundColor Yellow
        return $false
    }
}

# 在脚本开头添加全局变量控制详细程度
$VerbosePreference = "Continue"  # 设置为 "SilentlyContinue" 可关闭详细输出
$DebugPreference = "Continue"

# 暂停函数
function Pause {
    Write-Host "按任意键继续..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# 执行主函数
Main
