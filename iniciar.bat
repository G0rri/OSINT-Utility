@echo off
color 0A
title OSINT V2 Ultimate - Iniciador automatico

echo [*] Comprobando dependencias...

IF NOT EXIST "venv" (
    echo [*] Creando entorno virtual de Python ^(venv^)...
    python -m venv venv
)

echo [*] Activando entorno e instalando dependencias si faltan...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo [*] Abriendo OSINT V2...
python main.py

pause
