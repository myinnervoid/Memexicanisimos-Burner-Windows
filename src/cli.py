import argparse
import sys
import os
import signal
import time

from src.utils.i18n import setup_i18n
# Inicializar i18n
_ = setup_i18n()

from src.core.burner_core import BurnerEngine
from src.core.dependencies import get_missing_dependencies, get_package_names
from src.utils.notifications import send_notification

# Mantener referencia global para manejadores de señal
engine = None

def signal_handler(signum, frame):
    """Manejador de señales SIGINT y SIGTERM para cancelación segura."""
    print(_("\n[!] Señal de interrupción recibida. Cancelando operación..."))
    if engine:
        engine.cancel()
    sys.exit(1)

def print_progress(phase, val):
    """Imprime una barra de progreso simple en consola."""
    bar_length = 30
    filled_length = int(round(bar_length * val))
    percent = int(val * 100)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\r[{bar}] {percent}% - {phase}")
    sys.stdout.flush()

def print_log(msg):
    """Escribe los logs del motor a stdout."""
    # Opcional: Escribir a stdout si está activo un modo verboso, o simplemente guardar en logs
    pass

def main():
    global engine
    
    # Configurar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description=_("Memexicanisimos Burner CLI - Crea una USB booteable de Windows en Linux (UEFI/Secure Boot)")
    )
    parser.add_argument("--iso", required=True, help=_("Ruta al archivo ISO de Windows"))
    parser.add_argument("--device", required=True, help=_("Dispositivo de bloque de la USB (ej. /dev/sdX)"))
    parser.add_argument("--drivers", help=_("Ruta opcional a la carpeta de drivers VMD/RST"))
    parser.add_argument("--yes", action="store_true", help=_("Omitir confirmación destructiva"))
    
    args = parser.parse_args()
    
    # Validaciones iniciales
    if os.geteuid() != 0:
        print(_("Error: Esta aplicación requiere permisos de superusuario (root). Ejecuta con sudo."))
        sys.exit(1)
        
    if not os.path.exists(args.iso):
        print(_("Error: El archivo ISO especificado no existe."))
        sys.exit(1)
        
    if not args.device.startswith("/dev/"):
        print(_("Error: Dispositivo de bloque inválido. Debe comenzar con /dev/"))
        sys.exit(1)
        
    # Validar dependencias requeridas
    missing = get_missing_dependencies()
    if missing:
        pkgs = get_package_names(missing)
        print(_("Faltan las siguientes dependencias obligatorias: {tools}").format(tools=", ".join(missing)))
        print(_("Instálalas en tu sistema usando el administrador de paquetes (paquetes: {pkgs})").format(pkgs=", ".join(pkgs)))
        sys.exit(1)
        
    # Advertencia destructiva
    if not args.yes:
        confirm = input(_("¡ADVERTENCIA! Se borrará todo el contenido en {dev}. ¿Continuar? [s/N]: ").format(dev=args.device))
        if confirm.lower() not in ["s", "si", "y", "yes"]:
            print(_("Operación cancelada."))
            sys.exit(0)
            
    print(_("Iniciando creación de USB booteable..."))
    engine = BurnerEngine(args.iso, args.device, args.drivers)
    
    try:
        engine.execute(print_progress, print_log)
        print(_("\n✔️ USB booteable creada correctamente."))
        send_notification(_("Éxito"), _("USB booteable creada correctamente."), "normal")
    except Exception as e:
        print(f"\n❌ {_('Error')}: {e}")
        send_notification(_("Error"), _("Ocurrió un error al crear la USB."), "critical")
        sys.exit(1)

if __name__ == "__main__":
    main()
