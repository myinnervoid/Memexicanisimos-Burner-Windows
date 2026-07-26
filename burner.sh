#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Comprobar entorno gráfico
if [ -z "$DISPLAY" ]; then
    echo "No se detecta entorno gráfico. Esta aplicación requiere GUI."
    echo "Si estás en una terminal remota, conéctate con X11 forwarding (ssh -X)."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Asegurar permisos de ejecución del binario portable
if [ -f "$SCRIPT_DIR/burner" ]; then
    chmod +x "$SCRIPT_DIR/burner" 2>/dev/null || true
fi

# 2. Elegir el elevador de privilegios gráfico
if command -v pkexec &>/dev/null; then
    LAUNCHER="pkexec"
elif command -v gksudo &>/dev/null; then
    LAUNCHER="gksudo"
elif command -v kdesu &>/dev/null; then
    LAUNCHER="kdesu"
else
    echo "No se encontró una herramienta gráfica de permisos (pkexec, gksudo, kdesu)."
    echo "Por favor, ejecuta manualmente desde la terminal:"
    echo "  sudo $SCRIPT_DIR/burner"
    read -p "Presiona Enter para salir..."
    exit 1
fi

# 3. Lanzar desvinculado de la terminal para evitar SIGHUP al cerrar la consola
if tty -s; then
    # Lanzar de forma desvinculada usando setsid
    setsid $LAUNCHER "$SCRIPT_DIR/burner" >/dev/null 2>&1 &
else
    # Ejecución directa (doble clic)
    exec $LAUNCHER "$SCRIPT_DIR/burner"
fi
