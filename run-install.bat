@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Applio 使用UV安装

echo 欢迎使用Applio安装程序！(使用UV)
echo.

set "INSTALL_DIR=%cd%"
set "VENV_DIR=%INSTALL_DIR%\.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "UV_EXE=%VENV_DIR%\Scripts\uv.exe"

set "startTime=%TIME%"
set "startHour=%TIME:~0,2%"
set "startMin=%TIME:~3,2%"
set "startSec=%TIME:~6,2%"
set /a startHour=1%startHour% - 100
set /a startMin=1%startMin% - 100
set /a startSec=1%startSec% - 100
set /a startTotal = startHour*3600 + startMin*60 + startSec

call :check_existing_venv
if errorlevel 1 exit /b 1

call :check_uv
if errorlevel 1 exit /b 1

call :select_backend
if errorlevel 1 exit /b 1

call :create_uv_env
if errorlevel 1 exit /b 1

call :install_dependencies
if errorlevel 1 exit /b 1

set "endTime=%TIME%"
set "endHour=%TIME:~0,2%"
set "endMin=%TIME:~3,2%"
set "endSec=%TIME:~6,2%"
set /a endHour=1%endHour% - 100
set /a endMin=1%endMin% - 100
set /a endSec=1%endSec% - 100
set /a endTotal = endHour*3600 + endMin*60 + endSec
set /a elapsed = endTotal - startTotal
if %elapsed% lss 0 set /a elapsed += 86400
set /a hours = elapsed / 3600
set /a minutes = (elapsed %% 3600) / 60
set /a seconds = elapsed %% 60

echo 安装用时: %hours%小时, %minutes%分钟, %seconds%秒。
echo.

echo Applio已使用UV成功安装！
echo 请运行'run-applio.bat'启动Applio。
echo.
pause
exit /b 0

:check_existing_venv
if exist "%VENV_DIR%" (
    echo 发现已存在的.venv目录。
    
    :: 检查是否有Python进程正在使用该虚拟环境
    echo 检查是否有Python进程正在使用该虚拟环境...
    set "found_venv_processes=0"
    for /f "tokens=*" %%p in ('tasklist /fi "imagename eq python.exe" /fo csv /v ^| findstr /i "%VENV_DIR%"') do (
        set /a found_venv_processes+=1
    )
    
    if !found_venv_processes! gtr 0 (
        echo 检测到!found_venv_processes!个Python进程正在使用此虚拟环境。
        set /p "kill_processes=是否要结束这些进程以安全删除虚拟环境？(Y/N): "
        if /i "!kill_processes!"=="Y" (
            echo 请求管理员权限以结束Python进程...
            
            :: 创建临时管理员脚本 - 只终止与虚拟环境相关的进程
            echo @echo off > "%TEMP%\kill_python_venv.bat"
            echo for /f "tokens=2 delims=," %%p in ('tasklist /fi "imagename eq python.exe" /fo csv /v ^| findstr /i "%VENV_DIR%"') do ( >> "%TEMP%\kill_python_venv.bat"
            echo   taskkill /f /pid %%p >> "%TEMP%\kill_python_venv.bat"
            echo ) >> "%TEMP%\kill_python_venv.bat"
            echo exit >> "%TEMP%\kill_python_venv.bat"
            
            :: 使用提权运行脚本
            powershell -Command "Start-Process cmd -ArgumentList '/c %TEMP%\kill_python_venv.bat' -Verb RunAs"
            
            timeout /t 2 > nul
            echo 已尝试结束相关Python进程。
        ) else (
            echo 未结束Python进程，删除虚拟环境可能会失败。
        )
    )
    
    set /p "choice=是否要删除现有环境并重新安装？(Y/N): "
    if /i "!choice!"=="Y" (
        echo 正在删除现有的.venv目录...
        rmdir /s /q "%VENV_DIR%"
        if errorlevel 1 (
            echo 删除现有.venv目录失败。
            echo 这可能是因为：
            echo 1. 某些文件仍被程序占用
            echo 2. 需要管理员权限
            echo 请关闭所有相关程序后手动删除，或使用管理员权限运行此脚本。
            goto :error
        )
        echo 现有.venv目录已删除。
    ) else (
        echo 按照要求跳过安装。您可以尝试运行'run-applio.bat'。
        exit /b 0
    )
)
exit /b 0

:check_uv
echo 检查UV是否已安装...
where uv >nul 2>nul
if not errorlevel 1 (
    echo UV已安装在系统PATH中
    set "UV_CMD=uv"
    goto :uv_found
)

python -m uv --version >nul 2>nul
if not errorlevel 1 (
    echo UV已通过Python模块安装
    set "UV_CMD=python -m uv"
    goto :uv_found
)

echo UV未安装。请选择安装方式：
echo 1. 使用独立安装程序（推荐）
echo 2. 使用pip安装
echo 3. 使用WinGet安装（需要Windows包管理器）
echo 4. 使用Scoop安装（需要Scoop）
echo 5. 手动安装（取消）
set /p "install_choice=请输入选择编号: "

if "%install_choice%"=="1" (
    echo 使用独立安装程序安装UV...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if not errorlevel 1 (
        echo UV安装成功！
        set "UV_CMD=uv"
        goto :uv_found
    )
) else if "%install_choice%"=="2" (
    echo 使用pip安装UV...
    pip install uv
    if not errorlevel 1 (
        echo UV安装成功！
        set "UV_CMD=python -m uv"
        goto :uv_found
    )
) else if "%install_choice%"=="3" (
    echo 使用WinGet安装UV...
    winget install --id=astral-sh.uv -e
    if not errorlevel 1 (
        echo UV安装成功！
        set "UV_CMD=uv"
        goto :uv_found
    )
) else if "%install_choice%"=="4" (
    echo 使用Scoop安装UV...
    scoop install main/uv
    if not errorlevel 1 (
        echo UV安装成功！
        set "UV_CMD=uv"
        goto :uv_found
    )
) else (
    echo 取消安装。
    exit /b 1
)

echo UV安装失败，请参考 https://docs.astral.sh/uv/getting-started/installation/ 手动安装。
exit /b 1

:uv_found
echo 使用UV: !UV_CMD!
exit /b 0

:select_backend
echo 请选择要安装的PyTorch后端：
echo 1. cpu（仅CPU）
echo 2. cu118（CUDA 11.8）
echo 3. cu121（CUDA 12.1）
echo 4. cu124（CUDA 12.4）
echo 5. rocm（ROCm - 实验性）
echo 6. xpu（Intel GPU - 实验性）
set /p "backend_choice=请输入您的选择编号（例如，3表示cu121）: "

if "%backend_choice%"=="1" set "PYTORCH_EXTRA=cpu"
if "%backend_choice%"=="2" set "PYTORCH_EXTRA=cu118"
if "%backend_choice%"=="3" set "PYTORCH_EXTRA=cu121"
if "%backend_choice%"=="4" set "PYTORCH_EXTRA=cu124"
if "%backend_choice%"=="5" set "PYTORCH_EXTRA=rocm"
if "%backend_choice%"=="6" set "PYTORCH_EXTRA=xpu"

if not defined PYTORCH_EXTRA (
    echo 无效选择。请重新运行脚本。
    goto :error
)
echo 已选择后端: %PYTORCH_EXTRA%
echo.
exit /b 0

:create_uv_env
echo 正在使用UV创建虚拟环境...
%UV_CMD% venv "%VENV_DIR%" --python 3.10
if errorlevel 1 (
    echo 使用UV创建虚拟环境失败。
    echo 请检查Python 3.10是否已安装，或尝试手动创建虚拟环境。
    goto :error
)
echo 虚拟环境已成功创建于 %VENV_DIR%
echo.
exit /b 0

:install_dependencies
echo 正在使用UV为后端'%PYTORCH_EXTRA%'安装依赖...
echo 根据您的网络连接和系统配置，这可能需要一些时间。
call "%UV_EXE%" sync --extra %PYTORCH_EXTRA%
if errorlevel 1 (
    echo 使用UV sync安装依赖失败。
    echo 请检查网络连接和依赖项兼容性。
    goto :error
)
echo 依赖项安装完成。
echo.
exit /b 0

:error
echo 安装过程中发生错误。请查看上面的输出了解详情。
pause
exit /b 1
