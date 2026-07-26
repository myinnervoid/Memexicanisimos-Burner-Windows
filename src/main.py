import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess
import threading
import psutil
import sys
import signal
import logging
import urllib.request
import json

from src.utils.i18n import setup_i18n
# Inicializar internacionalización al principio
_ = setup_i18n()

from src.ui import design_tokens as dt
from src.core.burner_core import BurnerEngine
from src.core.dependencies import get_missing_dependencies, get_package_names, get_install_command
from src.utils.notifications import send_notification

# -------------------- Configuración global --------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

VERSION = "1.3.0"
GITHUB_API_URL = "https://api.github.com/repos/myinnervoid/Memexicanisimos-Burner-Windows/releases/latest"
LOCK_FILE = "/tmp/memexicanisimos-burner.lock"

# Configurar logging
LOG_DIR = os.path.expanduser("~/.cache/memexicanisimos-burner")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "memexicanisimos-burner.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------- Canvas Status Indicator --------------------
class StatusIndicator(tk.Canvas):
    def __init__(self, parent, size=14, color=dt.STATUS_OK, **kwargs):
        parent_bg = parent.cget("fg_color")
        if parent_bg == "transparent" or parent_bg is None:
            parent_bg = parent.winfo_toplevel().cget("fg_color")
        bg_hex = parent._apply_appearance_mode(parent_bg)
        
        super().__init__(parent, width=size, height=size, bg=bg_hex, highlightthickness=0, **kwargs)
        self.size = size
        self.oval = self.create_oval(1, 1, size-1, size-1, fill=color, outline="")
        
    def set_color(self, color):
        self.itemconfig(self.oval, fill=color)

# -------------------- Clase principal --------------------
class MemexicanisimosBurner(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Prevención de múltiples instancias ---
        self.ensure_single_instance()

        # --- Configuración de ventana ---
        self.title("Memexicanisimos Burner")
        self.geometry("820x680")
        self.minsize(780, 600)
        self.resizable(True, True)
        self.configure(fg_color=dt.BG_COLOR)

        # --- Cargar icono (compatible con PyInstaller) ---
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'src/assets/Icon.png')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'Icon.png')
        if os.path.exists(icon_path):
            self.iconphoto(True, tk.PhotoImage(file=icon_path))

        # --- Variables de estado ---
        self.iso_path = tk.StringVar()
        self.driver_path = tk.StringVar()
        self.selected_usb = tk.StringVar()
        self.is_working = False
        self.engine = None

        # --- Inicializar UI ---
        self.setup_ui()
        self.refresh_usb_list()

        # --- Verificar privilegios ---
        if os.geteuid() != 0:
            self.log(_("Advertencia: La aplicación se inició sin privilegios de administrador. Muchas funciones como escaneo y grabado no funcionarán correctamente. Usa burner.sh para ejecutarla."))
            self.status_indicator.set_color(dt.STATUS_WARN)

        # --- Verificar dependencias y versión (asíncrono) ---
        self.after(500, self.check_system_requirements)
        self.after(1000, self.check_for_updates)

    # -------------------- Instancia única --------------------
    def ensure_single_instance(self):
        try:
            if os.path.exists(LOCK_FILE):
                with open(LOCK_FILE, 'r') as f:
                    old_pid = f.read().strip()
                if old_pid and psutil.pid_exists(int(old_pid)):
                    proc = psutil.Process(int(old_pid))
                    if "burner" in proc.name().lower() or "python" in proc.name().lower():
                        messagebox.showwarning(_("Aplicación en ejecución"),
                                               _("Memexicanisimos Burner ya está abierto.\nCierra la otra ventana primero."))
                        sys.exit(0)
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logging.error(f"Lock file error: {e}")

    # -------------------- Interfaz de usuario --------------------
    def setup_ui(self):
        # Contenedor principal con scroll adaptable
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # --- Cabecera ---
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        self.status_indicator = StatusIndicator(header_frame, size=15, color=dt.STATUS_OK)
        self.status_indicator.pack(side="left", padx=(5, 10))

        title_label = ctk.CTkLabel(header_frame, text="Memexicanisimos Burner",
                                   font=dt.FONT_TITLE, text_color=dt.TEXT_MAIN)
        title_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(header_frame,
                                      text=_("Grabador de Windows ISO (UEFI/Secure Boot)"),
                                      font=dt.FONT_BASE, text_color=dt.TEXT_MUTED)
        subtitle_label.pack(side="left", padx=15)

        btn_help = ctk.CTkButton(header_frame, text=_("❓ Ayuda"), width=80, font=dt.FONT_BASE,
                                 fg_color="transparent", text_color=dt.TEXT_MUTED, hover_color=dt.BORDER_COLOR,
                                 command=self.show_help)
        btn_help.pack(side="right")

        # --- Tarjeta 1: Selección de ISO ---
        card1 = self.create_card(_("1️⃣  Selecciona la ISO de Windows"))
        iso_frame = ctk.CTkFrame(card1, fg_color="transparent")
        iso_frame.pack(fill="x", pady=(10, 0))
        
        self.iso_entry = ctk.CTkEntry(iso_frame, textvariable=self.iso_path,
                                      placeholder_text="/ruta/a/windows.iso",
                                      font=dt.FONT_BASE)
        self.iso_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_iso_browse = ctk.CTkButton(iso_frame, text=_("Buscar"), width=100, font=dt.FONT_BASE, command=self.select_iso)
        self.btn_iso_browse.pack(side="right")

        # --- Tarjeta 2: Unidad USB ---
        card2 = self.create_card(_("2️⃣  Elige la memoria USB (¡se borrará todo!)"))
        usb_frame = ctk.CTkFrame(card2, fg_color="transparent")
        usb_frame.pack(fill="x", pady=(10, 0))
        
        self.usb_menu = ctk.CTkOptionMenu(usb_frame, variable=self.selected_usb,
                                          values=[_("Analizando...")], font=dt.FONT_BASE)
        self.usb_menu.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_usb_refresh = ctk.CTkButton(usb_frame, text=_("⟳ Refrescar"), width=100, font=dt.FONT_BASE,
                                             fg_color=dt.COLOR_CANCEL, hover_color=dt.COLOR_CANCEL_HOVER,
                                             command=self.refresh_usb_list)
        self.btn_usb_refresh.pack(side="right")

        # --- Tarjeta 3: Opciones avanzadas (plegable) ---
        self.advanced_visible = False
        self.advanced_toggle_btn = ctk.CTkButton(self.main_frame, text=_("⚙️ Opciones avanzadas"), font=dt.FONT_BASE,
                                                 fg_color="transparent", text_color=dt.TEXT_MUTED,
                                                 command=self.toggle_advanced)
        self.advanced_toggle_btn.pack(anchor="w", pady=(10, 0))

        self.advanced_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")

        # Tarjeta interna de drivers
        card3 = self.create_card(_("💾 Drivers adicionales (VMD/RST)"), parent=self.advanced_frame)
        driver_frame = ctk.CTkFrame(card3, fg_color="transparent")
        driver_frame.pack(fill="x", pady=(10, 0))
        
        self.driver_entry = ctk.CTkEntry(driver_frame, textvariable=self.driver_path,
                                         placeholder_text=_("Carpeta con drivers extraídos"), font=dt.FONT_BASE)
        self.driver_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_driver_browse = ctk.CTkButton(driver_frame, text=_("Buscar"), width=100, font=dt.FONT_BASE, command=self.select_driver_folder)
        self.btn_driver_browse.pack(side="right")

        # --- Barra de progreso y fase ---
        self.phase_label = ctk.CTkLabel(self.main_frame, text="", font=dt.FONT_ITALIC,
                                        text_color=dt.TEXT_MUTED)
        self.phase_label.pack(anchor="w", pady=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill="x", pady=(5, 10))
        self.progress_bar.set(0)

        # --- Log técnico plegable ---
        self.log_visible = False
        self.log_toggle_btn = ctk.CTkButton(self.main_frame, text=_("📋 Mostrar detalles técnicos"), font=dt.FONT_BASE,
                                            fg_color="transparent", text_color=dt.TEXT_MUTED,
                                            command=self.toggle_log)
        self.log_toggle_btn.pack(anchor="w")

        self.log_box = ctk.CTkTextbox(self.main_frame, height=120, font=dt.FONT_MONO)
        self.log_box.configure(state="disabled")

        # --- Botones de acción ---
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 10))

        self.btn_start = ctk.CTkButton(btn_frame, text=_("⚠️ Crear USB booteable"),
                                       command=self.start_process_thread,
                                       fg_color=dt.COLOR_PRIMARY, hover_color=dt.COLOR_PRIMARY_HOVER,
                                       height=45, font=("Roboto", 16, "bold"))
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(btn_frame, text=_("Cancelar"),
                                        fg_color=dt.COLOR_CANCEL, hover_color=dt.COLOR_CANCEL_HOVER,
                                        height=45, font=dt.FONT_CARD_TITLE,
                                        state="disabled", command=self.cancel_operation)
        self.btn_cancel.pack(side="left", fill="x", expand=True)

    # -------------------- Tarjeta reusable --------------------
    def create_card(self, title, parent=None):
        if parent is None:
            parent = self.main_frame
        card = ctk.CTkFrame(parent, corner_radius=dt.CORNER_RADIUS, fg_color=dt.CARD_BG, border_color=dt.BORDER_COLOR, border_width=1)
        card.pack(fill="x", pady=8)
        header = ctk.CTkLabel(card, text=title, font=dt.FONT_CARD_TITLE, text_color=dt.TEXT_MAIN)
        header.pack(anchor="w", padx=dt.PADDING_CARD, pady=(12, 5))
        return card

    # -------------------- Alternar paneles --------------------
    def toggle_advanced(self):
        if self.advanced_visible:
            self.advanced_frame.pack_forget()
            self.advanced_toggle_btn.configure(text=_("⚙️ Opciones avanzadas"))
        else:
            self.advanced_frame.pack(fill="x", before=self.phase_label, pady=(5, 0))
            self.advanced_toggle_btn.configure(text=_("⚙️ Ocultar opciones avanzadas"))
        self.advanced_visible = not self.advanced_visible

    def toggle_log(self):
        if self.log_visible:
            self.log_box.pack_forget()
            self.log_toggle_btn.configure(text=_("📋 Mostrar detalles técnicos"))
        else:
            self.log_box.pack(fill="both", expand=True, before=self.log_toggle_btn, pady=(10, 5))
            self.log_toggle_btn.configure(text=_("📋 Ocultar detalles técnicos"))
        self.log_visible = not self.log_visible

    # -------------------- Lógica de selección --------------------
    def show_help(self):
        help_msg = _(
            "=== Memexicanisimos Burner - Manual de Ayuda ===\n\n"
            "1. ¿Por qué no detecta las USBs o da errores?\n"
            "Esta aplicación requiere ejecutarse con privilegios de superusuario (root) para poder formatear, particionar y escribir de forma directa en las unidades de disco físicas.\n"
            "Solución: Cierra esta ventana y ejecuta el programa mediante el lanzador 'burner.sh' (el cual te solicitará la contraseña de administrador gráficamente) o a través de terminal con 'sudo ./burner'.\n\n"
            "2. ¿Cómo funciona el grabado?\n"
            "Paso 1: Selecciona una imagen ISO oficial de Windows 10 u 11.\n"
            "Paso 2: Introduce una memoria USB de al menos 8 GB (¡Se borrará todo su contenido!).\n"
            "Paso 3: (Opcional) Si tu computadora es nueva y no detecta el disco duro SSD durante la instalación de Windows, activa 'Opciones avanzadas' y busca una carpeta con los drivers VMD/RST extraídos.\n"
            "Paso 4: Haz clic en 'Crear USB booteable'."
        )
        messagebox.showinfo(_("Ayuda"), help_msg)

    def select_iso(self):
        filename = filedialog.askopenfilename(filetypes=[("Archivos ISO", "*.iso")])
        if filename:
            self.iso_path.set(filename)

    def select_driver_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.driver_path.set(folder)

    def refresh_usb_list(self):
        try:
            cmd = "lsblk -d -o NAME,SIZE,MODEL,TRAN,TYPE | grep usb"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            devices = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 1:
                        dev_name = parts[0]
                        size = parts[1] if len(parts) > 1 else "?"
                        info = f"/dev/{dev_name} ({size})"
                        devices.append(info)
            if not devices:
                devices = [_("No se detectaron USBs")]
                self.selected_usb.set(_("No se detectaron USBs"))
            else:
                self.selected_usb.set(devices[0])
            self.usb_menu.configure(values=devices)
        except Exception as e:
            self.log(f"Error escaneando USBs: {e}")

    # -------------------- Máquina de Estados de la UI --------------------
    def set_ui_state(self, state: str):
        if state == "IDLE":
            self.is_working = False
            self.btn_start.configure(state="normal", text=_("⚠️ Crear USB booteable"), fg_color=dt.COLOR_PRIMARY)
            self.btn_cancel.configure(state="disabled")
            self.iso_entry.configure(state="normal")
            self.driver_entry.configure(state="normal")
            self.btn_iso_browse.configure(state="normal")
            self.btn_driver_browse.configure(state="normal")
            self.btn_usb_refresh.configure(state="normal")
            self.usb_menu.configure(state="normal")
            self.status_indicator.set_color(dt.STATUS_OK)
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.progress_bar.configure(mode="determinate")
            self.phase_label.configure(text="")
        elif state == "BURNING":
            self.is_working = True
            self.btn_start.configure(state="disabled", text=_("Grabando..."), fg_color="gray")
            self.btn_cancel.configure(state="normal")
            self.iso_entry.configure(state="disabled")
            self.driver_entry.configure(state="disabled")
            self.btn_iso_browse.configure(state="disabled")
            self.btn_driver_browse.configure(state="disabled")
            self.btn_usb_refresh.configure(state="disabled")
            self.usb_menu.configure(state="disabled")
            self.status_indicator.set_color(dt.STATUS_WARN)
            self.progress_bar.set(0)
            self.progress_bar.configure(mode="determinate")
        elif state == "SUCCESS":
            self.set_ui_state("IDLE")
            self.status_indicator.set_color(dt.STATUS_OK)
            self.phase_label.configure(text=_("✔️ Completado"))
        elif state == "ERROR":
            self.set_ui_state("IDLE")
            self.status_indicator.set_color(dt.STATUS_ERROR)
            self.phase_label.configure(text=_("❌ Falló"))

    # -------------------- Logging seguro --------------------
    def log(self, message):
        logging.info(message)
        self.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"> {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # -------------------- Hilos y Callbacks del Motor --------------------
    def start_process_thread(self):
        if self.is_working: return

        iso = self.iso_path.get()
        usb_display = self.selected_usb.get()
        usb_device = usb_display.split()[0] if usb_display else ""

        if not iso or not os.path.exists(iso):
            messagebox.showerror(_("Error"), _("Selecciona una ISO válida."))
            return
        if _("No se detectaron") in usb_display or not usb_device.startswith("/dev/"):
            messagebox.showerror(_("Error"), _("Selecciona una USB válida."))
            return

        if not messagebox.askyesno(_("¡ADVERTENCIA!"),
                                   _("Se borrará todo el contenido de:\n{device}\n\n¿Continuar?").format(device=usb_device)):
            return

        if os.geteuid() != 0:
            messagebox.showerror(_("Permisos"), _("Debes ejecutar esta aplicación con permisos de administrador.\nUsa el lanzador burner.sh"))
            return

        self.set_ui_state("BURNING")
        self.engine = BurnerEngine(iso, usb_device, self.driver_path.get())

        # Lanzar motor en segundo plano
        threading.Thread(target=self.run_engine, daemon=True).start()

    def run_engine(self):
        try:
            self.engine.execute(self.on_progress, self.on_log)
            self.after(0, self.on_success)
        except Exception as e:
            self.after(0, self.on_error, str(e))

    def cancel_operation(self):
        if self.engine:
            self.engine.cancel()
        self.set_ui_state("IDLE")

    # Callbacks thread-safe delegados con safe_ui_update (after)
    def on_progress(self, phase, val):
        self.after(0, self._safe_on_progress, phase, val)

    def _safe_on_progress(self, phase, val):
        self.phase_label.configure(text=phase)
        self.progress_bar.set(val)

    def on_log(self, msg):
        self.log(msg)

    def on_success(self):
        self.set_ui_state("SUCCESS")
        send_notification(_("Éxito"), _("USB booteable creada correctamente."), "normal")
        messagebox.showinfo(_("Éxito"), _("USB booteable creada correctamente."))

    def on_error(self, err_msg):
        self.set_ui_state("ERROR")
        if err_msg != "Operación cancelada":
            send_notification(_("Error"), _("Ocurrió un error al crear la USB."), "critical")
            messagebox.showerror(_("Error"), _("Ocurrió un error:\n{err_msg}").format(err_msg=err_msg))

    # -------------------- Dependencias --------------------
    def check_system_requirements(self):
        missing = get_missing_dependencies()
        if missing:
            msg = _("Faltan las siguientes herramientas requeridas:\n\n")
            for tool in missing:
                msg += f"• {tool} (paquete {get_package_names([tool])[0]})\n"
            msg += _("\n¿Quieres instalarlas automáticamente?")
            if messagebox.askyesno(_("Dependencias necesarias"), msg):
                self.install_dependencies(missing)

    def install_dependencies(self, missing):
        pkgs = get_package_names(missing)
        cmd = get_install_command(pkgs)
        
        if cmd is None:
            messagebox.showerror(_("Error"), _("No se detectó un gestor de paquetes soportado. Instala de forma manual."))
            return

        try:
            self.log(_("Instalando dependencias..."))
            # pkexec con listas de argumentos evita inyecciones de shell
            subprocess.run(["pkexec"] + cmd, check=True)
            messagebox.showinfo(_("Listo"), _("Dependencias instaladas correctamente."))
        except Exception as e:
            messagebox.showerror(_("Error"), _("Fallo al instalar dependencias:\n{err}").format(err=e))

    # -------------------- Actualizaciones --------------------
    def check_for_updates(self):
        try:
            with urllib.request.urlopen(GITHUB_API_URL, timeout=2) as response:
                data = json.loads(response.read().decode())
                latest = data.get("tag_name", "")
                if latest and latest != f"v{VERSION}":
                    if messagebox.askyesno(_("Actualización disponible"),
                                           _("Hay una nueva versión ({version}). ¿Abrir página de descarga?").format(version=latest)):
                        import webbrowser
                        webbrowser.open("https://github.com/myinnervoid/Memexicanisimos-Burner-Windows/releases/latest")
        except:
            pass

# -------------------- Limpieza del lockfile al cerrar --------------------
def cleanup_lock():
    try:
        os.remove(LOCK_FILE)
    except:
        pass

if __name__ == "__main__":
    signal.signal(signal.SIGHUP, signal.SIG_IGN)  # Ignorar cierre de terminal
    app = MemexicanisimosBurner()
    app.protocol("WM_DELETE_WINDOW", lambda: (cleanup_lock(), app.destroy()))
    app.mainloop()
    cleanup_lock()
