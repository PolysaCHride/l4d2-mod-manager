@echo off
rem L4D2 Mod Manager 启动脚本（保留控制台以便看到错误信息）
cd /d "%~dp0"
python main.py
if errorlevel 1 pause
