@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Lord Vault v4.2 PRO
python launchers\start.py %*
pause
