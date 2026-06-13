#!/bin/bash

# Activar colores para mensajes
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}[*] Comprobando dependencias...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${GREEN}[*] Creando entorno virtual de Python (venv)...${NC}"
    python3 -m venv venv
fi

echo -e "${GREEN}[*] Activando entorno e instalando dependencias si faltan...${NC}"
source venv/bin/activate

# REPARACIÓN: Forzamos el uso del ejecutable interno del venv para evitar usar el intérprete global
./venv/bin/python3 -m pip install -r requirements.txt

if [ ! -f "phoneinfoga" ]; then
    echo -e "${GREEN}[*] Descargando binario de PhoneInfoga para Linux...${NC}"
    curl -sSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install | bash
fi

echo -e "${GREEN}[*] Abriendo OSINT V2...${NC}"
./venv/bin/python3 main.py