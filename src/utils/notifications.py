import subprocess
import shutil
import os
import tkinter as tk
import customtkinter as ctk

def send_notification(title, body, urgency="normal"):
    """
    Envía una notificación de escritorio usando notify-send.
    Si no está instalado o falla, cae en un diálogo visual auto-ocultable si hay GUI activa.
    """
    # Intentar notify-send
    if shutil.which("notify-send"):
        try:
            # Urgencias soportadas por notify-send: low, normal, critical
            subprocess.run(["notify-send", "-u", urgency, title, body], check=True)
            return
        except Exception:
            pass

    # Fallback gráfico: Diálogo auto-ocultable si hay entorno gráfico
    if "DISPLAY" in os.environ and os.environ["DISPLAY"].strip():
        try:
            # Ejecutar diálogo temporal no bloqueante en el hilo de Tk
            root = ctk.CTk()
            root.title(title)
            root.geometry("380x130")
            root.resizable(False, False)
            root.attributes("-topmost", True)
            
            # Ajustar tema
            ctk.set_appearance_mode("System")
            
            frame = ctk.CTkFrame(root, corner_radius=10)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            emoji = "✔️" if urgency == "normal" else "❌"
            label = ctk.CTkLabel(frame, text=f"{emoji} {body}", font=("Roboto", 13), wraplength=340)
            label.pack(expand=True, padx=10, pady=10)
            
            # Auto-ocultar después de 4 segundos
            root.after(4000, root.destroy)
            root.mainloop()
        except Exception:
            # Evitar caídas si falla la GUI secundaria
            pass
    else:
        # Fallback de consola
        print(f"\n*** NOTIFICACIÓN [{urgency.upper()}]: {title} - {body} ***\n")
