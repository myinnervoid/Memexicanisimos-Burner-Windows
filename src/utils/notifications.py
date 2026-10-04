"""Módulo de notificaciones del sistema."""
import subprocess
import shutil
import os
import tkinter as tk # pylint: disable=unused-import

def send_notification(title, body, urgency="normal"):
    """
    Envía una notificación de escritorio usando notify-send.
    Si no está instalado o falla, cae en un diálogo visual auto-ocultable si hay GUI activa.
    """
    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", "-u", urgency, title, body], check=True)
            return
        except subprocess.SubprocessError:
            pass

    if "DISPLAY" in os.environ and os.environ["DISPLAY"].strip():
        try:
            # Import customtkinter locally to avoid issues on headless environments
            # pylint: disable=import-outside-toplevel
            import customtkinter as ctk

            root = ctk.CTk()
            root.title(title)
            root.geometry("380x130")
            root.resizable(False, False)
            root.attributes("-topmost", True)

            ctk.set_appearance_mode("System")

            frame = ctk.CTkFrame(root, corner_radius=10)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

            emoji = "✔️" if urgency == "normal" else "❌"
            label = ctk.CTkLabel(
                frame,
                text=f"{emoji} {body}",
                font=("Roboto", 13),
                wraplength=340
            )
            label.pack(expand=True, padx=10, pady=10)

            root.after(4000, root.destroy)
            root.mainloop()
        except tk.TclError:
            pass
        except ImportError:
            # Fallback si no hay customtkinter
            print(f"\n*** NOTIFICACIÓN GUI FALLIDA [{urgency.upper()}]: {title} - {body} ***\n")

    else:
        print(f"\n*** NOTIFICACIÓN [{urgency.upper()}]: {title} - {body} ***\n")
