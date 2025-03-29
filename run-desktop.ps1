<#
.SYNOPSIS
    Applio Desktop UI启动脚本 (PowerShell 版)
.DESCRIPTION
    激活虚拟环境并启动Applio的PyQt6桌面界面。
#>

# 设置中文编码环境
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 基本信息设置
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $scriptDir ".venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
$mainScript = Join-Path $scriptDir "desktop_ui\main.py"

# 检查虚拟环境
if (-not (Test-Path -Path $venvPath -PathType Container)) {
    Write-Host "虚拟环境 (.venv) 未找到。" -ForegroundColor Red
    Write-Host "请先运行 'run-install.ps1'。" -ForegroundColor Yellow
    Read-Host -Prompt "按 Enter 键退出"
    exit 1
}

# 检查激活脚本
if (-not (Test-Path -Path $activateScript -PathType Leaf)) {
    Write-Host "激活脚本未找到: $activateScript" -ForegroundColor Red
    Write-Host "请确保虚拟环境已正确创建。" -ForegroundColor Yellow
    Read-Host -Prompt "按 Enter 键退出"
    exit 1
}

# 检查主脚本
if (-not (Test-Path -Path $mainScript -PathType Leaf)) {
    Write-Host "桌面UI主脚本未找到: $mainScript" -ForegroundColor Red
    Read-Host -Prompt "按 Enter 键退出"
    exit 1
}

Write-Host "正在激活虚拟环境并启动 Applio Desktop UI..." -ForegroundColor Cyan

# 激活环境并运行主脚本
try {
    . $activateScript
    Write-Host "虚拟环境已激活。" -ForegroundColor Green
    python $mainScript
} catch {
    Write-Host "启动 Applio Desktop UI 时出错:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host -Prompt "按 Enter 键退出"
    exit 1
}

Write-Host "Applio Desktop UI 已关闭。"
Read-Host -Prompt "按 Enter 键关闭此窗口"
