@echo off
title Lualdi Configuratore Preventivi
color 0A
echo.
echo  LUALDI INDUSTRIA GRAFICA - Configuratore Preventivi
echo.
cd /d "%~dp0"
echo  Avvio in corso...
echo  Browser: http://localhost:8502
echo  Per fermare: Ctrl+C o chiudi questa finestra
echo.
python -m streamlit run app.py
pause
