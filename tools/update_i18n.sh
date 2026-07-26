#!/bin/bash
set -e

# Cambiar al directorio raíz del proyecto
cd "$(dirname "$0")/.."

echo "========================================================"
# Validar y compilar catálogos
python3 tools/msgfmt.py locale/es/LC_MESSAGES/memexicanisimos.po locale/es/LC_MESSAGES/memexicanisimos.mo
python3 tools/msgfmt.py locale/en/LC_MESSAGES/memexicanisimos.po locale/en/LC_MESSAGES/memexicanisimos.mo

echo "Traducciones actualizadas correctamente."
echo "========================================================"
