import shutil
import subprocess

TOOLS = {
    "wimsplit": "wimtools",
    "parted": "parted",
    "mkfs.fat": "dosfstools",
    "rsync": "rsync",
    "ntfs-3g": "ntfs-3g"
}

def get_missing_dependencies():
    """Retorna una lista de herramientas requeridas que no están instaladas en el PATH."""
    return [tool for tool, pkg in TOOLS.items() if shutil.which(tool) is None]

def get_package_names(missing_list):
    """Mapea los comandos ausentes con sus respectivos nombres de paquete."""
    return [TOOLS[tool] for tool in missing_list]

def get_install_command(packages):
    """Construye el comando de instalación basado en el gestor de paquetes de la distro."""
    if shutil.which("apt"):
        return ["apt-get", "install", "-y"] + packages
    elif shutil.which("dnf"):
        return ["dnf", "install", "-y"] + packages
    elif shutil.which("pacman"):
        return ["pacman", "-S", "--noconfirm"] + packages
    return None
