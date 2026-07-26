import os
import subprocess
import time
import shutil
import signal
import logging
import tempfile
import re
from pathlib import Path

class BurnerEngine:
    def __init__(self, iso_path: str, usb_device: str, driver_path: str = None):
        self.iso_path = iso_path
        self.usb_device = usb_device
        self.driver_path = driver_path
        self.current_process = None
        self.is_cancelled = False
        self.temp_iso_dir = None
        self.temp_usb_dir = None

    def log(self, message: str, log_callback):
        logging.info(message)
        if log_callback:
            log_callback(message)

    def run_command(self, args, log_callback, timeout=None):
        if self.is_cancelled:
            raise Exception("Operación cancelada por el usuario")
        
        self.log(f"Ejecutando comando: {' '.join(args)}", log_callback)
        
        # Iniciar proceso en su propio grupo para poder matar hijos
        self.current_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )
        
        try:
            stdout, stderr = self.current_process.communicate(timeout=timeout)
            if self.current_process.returncode != 0:
                raise Exception(f"Error ({self.current_process.returncode}): {stderr.strip()}")
            return stdout
        except subprocess.TimeoutExpired:
            self.cancel()
            raise Exception("La operación superó el límite de tiempo de espera")

    def execute(self, progress_callback, log_callback):
        try:
            self.is_cancelled = False
            progress_callback("Preparando...", 0.05)

            # Desmontar de manera forzada/lazy cualquier partición existente
            self.log(f"Desmontando particiones previas de {self.usb_device}...", log_callback)
            subprocess.run(["umount", "-l", f"{self.usb_device}1"], capture_output=True)
            subprocess.run(["umount", "-l", f"{self.usb_device}2"], capture_output=True)
            subprocess.run(f"umount -l {self.usb_device}* 2>/dev/null", shell=True)

            # Crear carpetas temporales únicas
            self.temp_iso_dir = tempfile.mkdtemp(prefix="memex_iso_")
            self.temp_usb_dir = tempfile.mkdtemp(prefix="memex_usb_")

            # Validación de espacio disponible (incluyendo margen de 100MB)
            iso_size = os.path.getsize(self.iso_path)
            driver_size = 0
            if self.driver_path and os.path.exists(self.driver_path):
                driver_size = sum(p.stat().st_size for p in Path(self.driver_path).rglob('*') if p.is_file())
            
            margin = 100 * 1024 * 1024 # 100 MB
            total_needed = iso_size + driver_size + margin

            # Obtener capacidad de USB por comandos seguros
            lsblk = subprocess.run(
                ["lsblk", "-b", "-n", "-o", "SIZE", self.usb_device],
                capture_output=True, text=True, check=True
            )
            usb_size = int(lsblk.stdout.strip().split()[0])

            self.log(f"Espacio necesario: {total_needed / (1024**3):.2f} GB (incluye margen de 100MB)", log_callback)
            self.log(f"Capacidad del USB: {usb_size / (1024**3):.2f} GB", log_callback)

            if total_needed > usb_size:
                raise Exception("La memoria USB no cuenta con espacio suficiente.")

            # Particionado seguro con GPT
            progress_callback("Creando particiones...", 0.15)
            self.run_command(["parted", "-s", self.usb_device, "mklabel", "gpt"], log_callback)
            self.run_command(["parted", "-s", self.usb_device, "mkpart", "primary", "fat32", "1MiB", "100%"], log_callback)
            time.sleep(1)

            usb_partition = f"{self.usb_device}1"
            if not os.path.exists(usb_partition):
                # Fallback para distribuciones NVMe u otras nomenclaturas (ej. /dev/nvme0n1p1 o /dev/mmcblk0p1)
                if f"{self.usb_device}p1" in os.listdir("/dev") or os.path.exists(f"{self.usb_device}p1"):
                    usb_partition = f"{self.usb_device}p1"
                else:
                    subprocess.run(["partprobe", self.usb_device], capture_output=True)
                    time.sleep(2)

            if not os.path.exists(usb_partition):
                raise Exception(f"No se pudo localizar la partición creada: {usb_partition}")

            # Formateo FAT32
            progress_callback("Formateando unidad (FAT32)...", 0.30)
            self.run_command(["mkfs.fat", "-F", "32", "-n", "WIN_INSTALL", usb_partition], log_callback)

            # Montar ISO y USB de forma segura
            progress_callback("Montando medios...", 0.40)
            self.run_command(["mount", "-o", "loop,ro", self.iso_path, self.temp_iso_dir], log_callback)
            self.run_command(["mount", usb_partition, self.temp_usb_dir], log_callback)

            # Copiar archivos base excluyendo instaladores pesados
            progress_callback("Copiando archivos base...", 0.50)
            rsync_cmd = [
                "rsync", "-r", "--info=progress2",
                "--exclude=sources/install.wim",
                "--exclude=sources/install.esd",
                f"{self.temp_iso_dir}/", f"{self.temp_usb_dir}/"
            ]
            self.run_command(rsync_cmd, log_callback)

            # Procesar instalador WIM o ESD
            wim_source = os.path.join(self.temp_iso_dir, "sources", "install.wim")
            if not os.path.exists(wim_source):
                wim_source = os.path.join(self.temp_iso_dir, "sources", "install.esd")
            
            wim_target_dir = os.path.join(self.temp_usb_dir, "sources")
            
            if os.path.exists(wim_source):
                size_gb = os.path.getsize(wim_source) / (1024**3)
                self.log(f"Archivo de instalación detectado: {os.path.basename(wim_source)} ({size_gb:.2f} GB)", log_callback)
                
                if size_gb > 4.0:
                    progress_callback("Dividiendo instalador (WIM/ESD)...", 0.70)
                    target_swm = os.path.join(wim_target_dir, "install.swm")
                    
                    # Ejecutar wimsplit y capturar progreso en tiempo real
                    self.log(f"Ejecutando wimsplit para {os.path.basename(wim_source)}...", log_callback)
                    wimsplit_cmd = ["wimsplit", wim_source, target_swm, "3800"]
                    self.current_process = subprocess.Popen(
                        wimsplit_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        preexec_fn=os.setsid
                    )
                    
                    # Leer la salida estándar de wimsplit para mostrar progreso real
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
                                # Escalar el progreso de wimsplit entre 0.70 y 0.90
                                progress_callback(f"Dividiendo instalador... {match.group(1)}%", 0.70 + (val * 0.20))
                    
                    self.current_process.communicate()
                    if self.current_process.returncode != 0:
                        raise Exception("Fallo al dividir el archivo install.wim/esd con wimsplit.")
                else:
                    progress_callback("Copiando instalador...", 0.80)
                    shutil.copy2(wim_source, os.path.join(wim_target_dir, os.path.basename(wim_source)))
            else:
                self.log("Aviso: No se detectó install.wim ni install.esd en la ISO.", log_callback)

            # Inyectar Drivers si fueron seleccionados
            if self.driver_path and os.path.exists(self.driver_path):
                progress_callback("Inyectando controladores...", 0.90)
                vmd_dest = os.path.join(self.temp_usb_dir, "Drivers", "VMD")
                os.makedirs(vmd_dest, exist_ok=True)
                
                # Copia recursiva segura de drivers
                self.run_command(["cp", "-r", f"{self.driver_path}/.", vmd_dest], log_callback)
                
                # Crear LEEME instructivo
                readme_path = os.path.join(self.temp_usb_dir, "LEEME_DRIVERS.txt")
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write("Si Windows 10/11 no detecta tu disco SSD durante la instalación:\n")
                    f.write("1. Selecciona 'Cargar controlador' (Load driver).\n")
                    f.write("2. Presiona 'Examinar' (Browse) y busca la carpeta: Drivers/VMD\n")
                    f.write("3. Selecciona el driver correspondiente para habilitar tu unidad NVMe/Intel RST.\n")

            progress_callback("Finalizando y sincronizando...", 0.95)
            self.run_command(["sync"], log_callback)
            
            # Limpieza limpia
            self.cleanup(log_callback)
            progress_callback("Completado", 1.0)
            
        except Exception as e:
            if self.is_cancelled:
                self.log("Proceso abortado por el usuario.", log_callback)
                raise Exception("Operación cancelada")
            else:
                self.log(f"Error crítico en el motor: {e}", log_callback)
                self.cleanup(log_callback)
                raise e

    def cancel(self):
        self.is_cancelled = True
        if self.current_process:
            try:
                # Matar el grupo de procesos completo
                pgid = os.getpgid(self.current_process.pid)
                os.killpg(pgid, signal.SIGTERM)
            except Exception as e:
                logging.error(f"Error al enviar SIGTERM a la operación: {e}")

    def cleanup(self, log_callback):
        # Desmontar carpetas de forma segura
        for path in [self.temp_usb_dir, self.temp_iso_dir]:
            if path and os.path.exists(path):
                # Verificar si está montado antes de desmontar
                is_mounted = subprocess.run(["mountpoint", "-q", path]).returncode == 0
                if is_mounted:
                    self.log(f"Desmontando de forma diferida: {path}", log_callback)
                    subprocess.run(["umount", "-l", path], capture_output=True)
                
                # Esperar y remover directorio
                time.sleep(0.5)
                try:
                    os.rmdir(path)
                except Exception as e:
                    self.log(f"No se pudo eliminar la carpeta temporal {path}: {e}", log_callback)
