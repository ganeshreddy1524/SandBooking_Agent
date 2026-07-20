@echo off
title Karimnagar Sand Availability Agent
echo Starting Karimnagar Sand Availability Monitoring Agent...
cd /d "%~dp0"
python monitor.py
pause
