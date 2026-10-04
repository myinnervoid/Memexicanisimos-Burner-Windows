"""Módulo central para la creación de memorias USB booteables de Windows."""
import os
import subprocess
import time
import shutil
import signal
import logging
import tempfile
import re
from pathlib import Path


class BurnerEngineError(Exception):
    """Excepción base para errores en el motor."""


class BurnerEngine:
    """Motor central para la creación de la USB booteable."""
    def __init__(self, iso_path: str, usb_device: str, driver_path: str = None):
        self.iso_path = iso_path
        self.usb_device = usb_device
        self.driver_path = driver_path
        self.current_process = None
        self.is_cancelled = False
        self.temp_iso_dir = None
        self.temp_usb_dir = None

    def log(self, message: str, log_callback):
        """Registra un mensaje y llama al callback si existe."""
        logging.info("%s", message)
        if log_callback:
            log_callback(message)

    def run_command(self, args, log_callback, timeout=None):
        """Ejecuta un comando en el sistema y captura su salida."""
        if self.is_cancelled:
            raise BurnerEngineError("Operación cancelada por el usuario")

        self.log(f"Ejecutando comando: {' '.join(args)}", log_callback)

        with subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        ) as self.current_process:
            try:
                stdout, stderr = self.current_process.communicate(timeout=timeout)
                if self.current_process.returncode != 0:
                    raise BurnerEngineError(
                        f"Error ({self.current_process.returncode}): {stderr.strip()}"
                    )
                return stdout
            except subprocess.TimeoutExpired as exc:
                self.cancel()
                raise BurnerEngineError("La operación superó el límite de tiempo") from exc

    def _unmount_partitions(self, log_callback):
        """Desmonta las particiones del dispositivo USB antes de comenzar."""
        self.log(f"Desmontando particiones previas de {self.usb_device}...", log_callback)
        subprocess.run(["umount", "-l", f"{self.usb_device}1"], capture_output=True, check=False)
        subprocess.run(["umount", "-l", f"{self.usb_device}2"], capture_output=True, check=False)
        subprocess.run(f"umount -l {self.usb_device}* 2>/dev/null", shell=True, check=False)

    def _calculate_space_requirements(self, log_callback) -> bool:
        """Calcula si hay espacio suficiente y devuelve True si lo hay."""
        iso_size = os.path.getsize(self.iso_path)
        driver_size = 0
        if self.driver_path and os.path.exists(self.driver_path):
            driver_size = sum(
                p.stat().st_size for p in Path(self.driver_path).rglob('*') if p.is_file()
            )

        margin = 100 * 1024 * 1024  # 100 MB
        total_needed = iso_size + driver_size + margin

        lsblk = subprocess.run(
            ["lsblk", "-b", "-n", "-o", "SIZE", self.usb_device],
            capture_output=True, text=True, check=True
        )
        usb_size = int(lsblk.stdout.strip().split()[0])

        req_gb = total_needed / (1024**3)
        self.log(f"Espacio necesario: {req_gb:.2f} GB (incluye margen de 100MB)", log_callback)
        self.log(f"Capacidad del USB: {usb_size / (1024**3):.2f} GB", log_callback)

        if total_needed > usb_size:
            raise BurnerEngineError("La memoria USB no cuenta con espacio suficiente.")
        return True

    def _create_partitions(self, log_callback):
        """Crea las particiones necesarias en el dispositivo USB."""
        self.run_command(["parted", "-s", self.usb_device, "mklabel", "gpt"], log_callback)
        self.run_command(
            ["parted", "-s", self.usb_device, "mkpart", "primary", "fat32", "1MiB", "100%"],
            log_callback
        )
        time.sleep(1)

        usb_partition = f"{self.usb_device}1"
        if not os.path.exists(usb_partition):
            p1_dev = f"{self.usb_device}p1"
            if p1_dev in os.listdir("/dev") or os.path.exists(p1_dev):
                usb_partition = p1_dev
            else:
                subprocess.run(["partprobe", self.usb_device], capture_output=True, check=False)
                time.sleep(2)

        if not os.path.exists(usb_partition):
            raise BurnerEngineError(f"No se pudo localizar la partición creada: {usb_partition}")

        return usb_partition

    def _process_installer(self, log_callback, progress_callback):
        """Procesa el archivo install.wim/esd, dividiéndolo si es necesario."""
        wim_source = os.path.join(self.temp_iso_dir, "sources", "install.wim")
        if not os.path.exists(wim_source):
            wim_source = os.path.join(self.temp_iso_dir, "sources", "install.esd")

        wim_target_dir = os.path.join(self.temp_usb_dir, "sources")

        if os.path.exists(wim_source):
            size_gb = os.path.getsize(wim_source) / (1024**3)
            self.log(
                f"Archivo detectado: {os.path.basename(wim_source)} ({size_gb:.2f} GB)",
                log_callback
            )

            if size_gb > 4.0:
                progress_callback("Dividiendo instalador (WIM/ESD)...", 0.70)
                target_swm = os.path.join(wim_target_dir, "install.swm")

                self.log(
                    f"Ejecutando wimsplit para {os.path.basename(wim_source)}...",
                    log_callback
                )
                wimsplit_cmd = ["wimsplit", wim_source, target_swm, "3800"]
                with subprocess.Popen(
                    wimsplit_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True
                ) as self.current_process:

                    percent_pattern = re.compile(r"(\d+)%")
                    while True:
                        line = self.current_process.stdout.readline()
                        if not line:
                            break
                        line_str = line.strip()
                        if line_str:
                            self.log(line_str, log_callback)
                            match = percent_pattern.search(line_str)
                            if match:
                                val = float(match.group(1)) / 100.0
                                progress_callback(
                                    f"Dividiendo instalador... {match.group(1)}%",
                                    0.70 + (val * 0.20)
                                )

                    self.current_process.communicate()
                    if self.current_process.returncode != 0:
                        raise BurnerEngineError("Fallo al dividir install.wim/esd con wimsplit.")
            else:
                progress_callback("Copiando instalador...", 0.80)
                shutil.copy2(wim_source, os.path.join(wim_target_dir, os.path.basename(wim_source)))
        else:
            self.log("Aviso: No se detectó install.wim ni install.esd en la ISO.", log_callback)

    def _inject_drivers(self, log_callback, progress_callback):
        """Inyecta los controladores seleccionados en el USB."""
        if self.driver_path and os.path.exists(self.driver_path):
            progress_callback("Inyectando controladores...", 0.90)
            vmd_dest = os.path.join(self.temp_usb_dir, "Drivers", "VMD")
            os.makedirs(vmd_dest, exist_ok=True)

            self.run_command(["cp", "-r", f"{self.driver_path}/.", vmd_dest], log_callback)

            readme_path = os.path.join(self.temp_usb_dir, "LEEME_DRIVERS.txt")
            with open(readme_path, "w", encoding="utf-8") as file:
                file.write("Si Windows no detecta tu disco SSD durante la instalación:\n")
                file.write("1. Selecciona 'Cargar controlador' (Load driver).\n")
                file.write("2. Presiona 'Examinar' (Browse) y busca: Drivers/VMD\n")
                file.write("3. Selecciona el driver para habilitar NVMe/Intel RST.\n")

    def execute(self, progress_callback, log_callback):
        """Ejecuta el proceso completo de creación del USB booteable."""
        try:
            self.is_cancelled = False
            progress_callback("Preparando...", 0.05)

            self._unmount_partitions(log_callback)

            self.temp_iso_dir = tempfile.mkdtemp(prefix="memex_iso_")
            self.temp_usb_dir = tempfile.mkdtemp(prefix="memex_usb_")

            self._calculate_space_requirements(log_callback)

            progress_callback("Creando particiones...", 0.15)
            usb_partition = self._create_partitions(log_callback)

            progress_callback("Formateando unidad (FAT32)...", 0.30)
            mkfs_cmd = ["mkfs.fat", "-F", "32", "-n", "WIN_INSTALL", usb_partition]
            self.run_command(mkfs_cmd, log_callback)

            progress_callback("Montando medios...", 0.40)
            mount_iso = ["mount", "-o", "loop,ro", self.iso_path, self.temp_iso_dir]
            self.run_command(mount_iso, log_callback)
            self.run_command(["mount", usb_partition, self.temp_usb_dir], log_callback)

            progress_callback("Copiando archivos base...", 0.50)
            rsync_cmd = [
                "rsync", "-r", "--info=progress2",
                "--exclude=sources/install.wim",
                "--exclude=sources/install.esd",
                f"{self.temp_iso_dir}/", f"{self.temp_usb_dir}/"
            ]
            self.run_command(rsync_cmd, log_callback)

            self._process_installer(log_callback, progress_callback)

            self._inject_drivers(log_callback, progress_callback)

            progress_callback("Finalizando y sincronizando...", 0.95)
            self.run_command(["sync"], log_callback)

            self.cleanup(log_callback)
            progress_callback("Completado", 1.0)

        except Exception as exc:
            if self.is_cancelled:
                self.log("Proceso abortado por el usuario.", log_callback)
                raise BurnerEngineError("Operación cancelada") from exc
            self.log(f"Error crítico en el motor: {exc}", log_callback)
            self.cleanup(log_callback)
            raise

    def cancel(self):
        """Cancela la operación en curso."""
        self.is_cancelled = True
        if self.current_process:
            try:
                pgid = os.getpgid(self.current_process.pid)
                os.killpg(pgid, signal.SIGTERM)
            except OSError as exc:
                logging.error("Error al enviar SIGTERM a la operación: %s", exc)

    def cleanup(self, log_callback):
        """Desmonta y elimina los directorios temporales."""
        for path in [self.temp_usb_dir, self.temp_iso_dir]:
            if path and os.path.exists(path):
                is_mounted = subprocess.run(["mountpoint", "-q", path], check=False).returncode == 0
                if is_mounted:
                    self.log(f"Desmontando de forma diferida: {path}", log_callback)
                    subprocess.run(["umount", "-l", path], capture_output=True, check=False)

                time.sleep(0.5)
                try:
                    os.rmdir(path)
                except OSError as exc:
                    self.log(f"No se pudo eliminar la carpeta temporal {path}: {exc}", log_callback)
