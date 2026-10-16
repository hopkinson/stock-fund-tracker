@echo off
chcp 65001 >nul
title PortfolioHub 资产罗盘
echo =======================================================
echo          PortfolioHub 资产罗盘 监控系统启动中...
echo          天天基金 · 雪球基金 · 东方财富 实时多账户聚合
echo =======================================================
echo.
echo 正在启动后端服务与定时行情抓取引擎...
start "" "http://127.0.0.1:8000"
d:\fork\gupiao\venv\Scripts\python.exe -m uvicorn main:app --app-dir d:\fork\gupiao\backend --host 127.0.0.1 --port 8000
pause
