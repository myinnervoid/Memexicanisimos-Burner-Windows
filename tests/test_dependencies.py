import shutil
from src.core.dependencies import get_missing_dependencies, get_package_names, get_install_command

def test_get_missing_dependencies(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda x: None)
    missing = get_missing_dependencies()
    assert set(missing) == {"wimsplit", "parted", "mkfs.fat", "rsync", "ntfs-3g"}

    monkeypatch.setattr(shutil, 'which', lambda x: "some/path" if x == "rsync" else None)
    missing = get_missing_dependencies()
    assert "rsync" not in missing

def test_get_package_names():
    names = get_package_names(["wimsplit", "mkfs.fat"])
    assert set(names) == {"wimtools", "dosfstools"}

def test_get_install_command_apt(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda x: "path/to/apt" if x == "apt" else None)
    cmd = get_install_command(["wimtools"])
    assert cmd == ["apt-get", "install", "-y", "wimtools"]

def test_get_install_command_dnf(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda x: "path/to/dnf" if x == "dnf" else None)
    cmd = get_install_command(["wimtools"])
    assert cmd == ["dnf", "install", "-y", "wimtools"]

def test_get_install_command_pacman(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda x: "path/to/pacman" if x == "pacman" else None)
    cmd = get_install_command(["wimtools"])
    assert cmd == ["pacman", "-S", "--noconfirm", "wimtools"]

def test_get_install_command_none(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda x: None)
    cmd = get_install_command(["wimtools"])
    assert cmd is None
