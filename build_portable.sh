#!/bin/bash
set -e

echo "========================================================"
echo " Memexicanisimos Burner - Compilador de Versión Portable"
echo "========================================================"
echo ""

# Cambiar al directorio del script
cd "$(dirname "$0")"

# 1. Configurar entorno de compilación
echo "[1/5] Inicializando entorno de compilación virtual..."
python3 -m venv build_venv
source build_venv/bin/activate

echo "[2/5] Instalando dependencias necesarias (PyInstaller, CustomTkinter, Psutil)..."
pip install --upgrade pip
pip install customtkinter psutil pyinstaller

# Compilar traducciones antes del empaquetado
echo "[2.5/5] Compilando catálogos de traducción..."
python3 tools/msgfmt.py locale/es/LC_MESSAGES/memexicanisimos.po locale/es/LC_MESSAGES/memexicanisimos.mo
python3 tools/msgfmt.py locale/en/LC_MESSAGES/memexicanisimos.po locale/en/LC_MESSAGES/memexicanisimos.mo

# 2. Compilar con PyInstaller incluyendo hidden imports e i18n data
echo "[3/5] Compilando ejecutable binario independiente con PyInstaller..."
pyinstaller --noconfirm --clean --onefile --windowed \
  --add-data "src/assets/Icon.png:src/assets" \
  --add-data "locale:locale" \
  --hidden-import src.ui.design_tokens \
  --hidden-import src.core.burner_core \
  --hidden-import src.core.dependencies \
  --hidden-import src.utils.notifications \
  --hidden-import src.utils.i18n \
  --name "burner" src/main.py

# 3. Estructurar la carpeta de distribución
echo "[4/5] Creando la estructura portable de la aplicación..."
DIST_DIR="dist/Memexicanisimos-Burner"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Copiar el binario compilado
cp dist/burner "$DIST_DIR/"

# Copiar el lanzador de shell pkexec
cp burner.sh "$DIST_DIR/"
chmod +x "$DIST_DIR/burner.sh"

# Copiar el icono para accesos directos
cp src/assets/Icon.png "$DIST_DIR/"

# 4. Empaquetar y calcular integridad
echo "[5/5] Comprimiendo a .tar.gz y calculando checksum de integridad..."
cd dist
tar -czf Memexicanisimos-Burner.tar.gz Memexicanisimos-Burner

# Generar checksum SHA256 para validaciones de descarga
sha256sum Memexicanisimos-Burner.tar.gz > Memexicanisimos-Burner.tar.gz.sha256

echo ""
echo "========================================================"
echo " Compilación completada con éxito."
echo " Archivo de distribución: dist/Memexicanisimos-Burner.tar.gz"
echo " Checksum SHA256: dist/Memexicanisimos-Burner.tar.gz.sha256"
echo "========================================================"
