import os
import pytest
import subprocess
import tempfile

@pytest.fixture(scope="function")
def loopback_device():
    """
    Crea un disco virtual de 8GB disperso y lo asocia a un loopback libre.
    """
    if os.geteuid() != 0:
        pytest.skip("Esta prueba requiere privilegios root (sudo).")

    img_fd, img_path = tempfile.mkstemp(prefix="memex_test_", suffix=".img")
    os.close(img_fd)
    
    try:
        subprocess.run(["truncate", "-s", "8G", img_path], check=True)
        losetup = subprocess.run(
            ["losetup", "-f", "--show", img_path],
            capture_output=True, text=True, check=True
        )
        loop_dev = losetup.stdout.strip()
        yield loop_dev
    finally:
        if 'loop_dev' in locals():
            subprocess.run(["losetup", "-d", loop_dev], capture_output=True)
        if os.path.exists(img_path):
            os.remove(img_path)

@pytest.fixture(scope="function")
def fake_iso():
    """
    Crea un archivo de imagen formateado en FAT32 que contiene un install.wim de 5GB disperso,
    simulando una ISO de Windows lista para ser montada.
    """
    if os.geteuid() != 0:
        pytest.skip("Esta prueba requiere privilegios root (sudo).")

    iso_fd, iso_path = tempfile.mkstemp(prefix="fake_win_", suffix=".iso")
    os.close(iso_fd)
    
    mnt_dir = tempfile.mkdtemp(prefix="fake_mnt_")
    
    try:
        # Crear archivo de 50MB
        subprocess.run(["truncate", "-s", "50M", iso_path], check=True)
        # Formatear como FAT32 para poder montarlo y escribirle
        subprocess.run(["mkfs.fat", "-F", "32", iso_path], check=True)
        
        # Montar y crear la estructura de Windows
        subprocess.run(["mount", "-o", "loop", iso_path, mnt_dir], check=True)
        os.makedirs(os.path.join(mnt_dir, "sources"), exist_ok=True)
        
        # Crear install.wim de 5GB (disperso, no consume espacio)
        wim_path = os.path.join(mnt_dir, "sources", "install.wim")
        subprocess.run(["truncate", "-s", "5G", wim_path], check=True)
        
        # Crear otros archivos base
        with open(os.path.join(mnt_dir, "bootmgr"), "w") as f:
            f.write("bootmgr data")
            
        yield iso_path
        
    finally:
        subprocess.run(["umount", "-l", mnt_dir], capture_output=True)
        if os.path.exists(mnt_dir):
            try:
                os.rmdir(mnt_dir)
            except:
                pass
        if os.path.exists(iso_path):
            os.remove(iso_path)
