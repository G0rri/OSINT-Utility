#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd "$(dirname "$0")"

echo -e "${GREEN}[*] Comprobando dependencias...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${GREEN}[*] Creando entorno virtual de Python (venv)...${NC}"
    python3 -m venv venv
fi

echo -e "${GREEN}[*] Activando entorno e instalando dependencias si faltan...${NC}"
# Usamos el ejecutable interno del venv para no depender del intérprete global
./venv/bin/python3 -m pip install -r requirements.txt

if [ ! -f "phoneinfoga" ]; then
    echo -e "${YELLOW}[!] El binario de PhoneInfoga no está presente.${NC}"
    echo -e "${YELLOW}    Este proyecto NO descarga ni ejecuta scripts remotos de forma"
    echo -e "    automática. Para instalarlo, revisa primero el script oficial y"
    echo -e "    ejecútalo tú mismo:${NC}"
    echo ""
    echo "    curl -sSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install -o /tmp/phoneinfoga-install.sh"
    echo "    less /tmp/phoneinfoga-install.sh    # revísalo antes de ejecutarlo"
    echo "    bash /tmp/phoneinfoga-install.sh"
    echo ""
    echo -e "${YELLOW}    O descarga el binario firmado desde las releases oficiales:${NC}"
    echo "    https://github.com/sundowndev/phoneinfoga/releases"
    echo ""
    echo -e "${YELLOW}    El resto de módulos funcionarán con normalidad sin él.${NC}"
    echo ""
elif [ ! -x "phoneinfoga" ]; then
    echo -e "${GREEN}[*] Otorgando permisos de ejecución al binario de PhoneInfoga...${NC}"
    chmod +x phoneinfoga
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo -e "${YELLOW}[!] No existe .env. Copiando la plantilla .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}    Edita .env para añadir tus claves de API.${NC}"
fi

echo -e "${GREEN}[*] Abriendo OSINT V2...${NC}"
exec ./venv/bin/python3 main.py
