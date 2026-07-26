# 🔥 Memexicanisimos Burner

![Icono](Logos/Logo%20Readme.png)

![Versión](https://img.shields.io/badge/version-1.3.0-orange)
![Licencia](https://img.shields.io/badge/license-MIT-green)
![Plataforma](https://img.shields.io/badge/platform-Linux%20(x86__64)-lightgrey)
[![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)](https://github.com/myinnervoid/Memexicanisimos-Burner-Windows)

Una herramienta ultra-sencilla y profesional para crear memorias USB de instalación de Windows desde tu distribución Linux de manera rápida, segura y sin estrés. Soporta tanto interfaz gráfica (GUI) moderna como interfaz de consola (CLI).

---

## 🚀 Novedades en la Versión 1.3.0

*   **Internacionalización completa (i18n)**: Traducción nativa al inglés y español basada en el idioma de tu sistema operativo (`LANG`).
*   **Notificaciones nativas**: Envío de avisos visuales (éxito o fallos) mediante `notify-send` con diálogos gráficos auto-ocultables en su ausencia.
*   **Consola CLI independiente**: Nueva herramienta de línea de comandos para automatizar el grabado sin necesidad de cargar la interfaz gráfica.
*   **División inteligente WIM/ESD**: Automatiza la partición de instaladores de Windows mayores a 4 GB para cumplir los requisitos de compatibilidad FAT32 en placas UEFI modernas.
*   **Drivers VMD/RST**: Opción de inyectar controladores específicos de almacenamiento de Intel directamente para que Windows detecte tus discos SSD.

---

## 🌍 Internacionalización (i18n)

La aplicación detecta automáticamente el idioma de tu sistema operativo (`LANG`) y ofrece interfaz en:
*   **Español (es)**
*   **Inglés (en)** (como idioma predeterminado)

Para forzar un idioma en específico, ejecuta la app definiendo la variable de entorno:
```bash
LANG=en_US.UTF-8 ./burner.sh
```

---

## 💻 ¿Cómo lo uso? (Modo Gráfico / GUI)

1. **Descarga**: Obtén el archivo comprimido `Memexicanisimos-Burner.tar.gz` desde la sección de [Releases (Último Lanzamiento)](https://github.com/myinnervoid/Memexicanisimos-Burner-Windows/releases/latest).
2. **Extrae**: Haz clic derecho sobre el archivo descargado y selecciona **"Extraer aquí"** (o ejecuta `tar -xzf Memexicanisimos-Burner.tar.gz` en tu terminal).
3. **Ejecuta**: Entra a la carpeta extraída, haz doble clic en `burner.sh` (o ejecútalo con `./burner.sh`). Introduce tu contraseña de administrador cuando aparezca la ventana de autorización y ¡listo!

---

## 🛠️ Interfaz de Línea de Comandos (CLI)

Para sistemas de administración por consola, servidores o automatización de scripts:

```bash
sudo bin/memex-burner --iso /ruta/a/windows.iso --device /dev/sdX
```

### Opciones de Consola:
*   `--iso`: (Requerido) Ruta de la imagen `.iso`.
*   `--device`: (Requerido) Dispositivo USB (`/dev/sdX`).
*   `--drivers`: (Opcional) Ruta de la carpeta de drivers extraídos.
*   `--yes`: (Opcional) Omitir confirmación interactiva de formateo.

---

## 📦 Requisitos del Sistema

Para el correcto funcionamiento del formateo, copia y notificaciones:

* **Debian / Ubuntu y derivados**:
  ```bash
  sudo apt install wimtools parted dosfstools rsync ntfs-3g policykit-1 libnotify-bin
  ```
* **Fedora y derivados**:
  ```bash
  sudo dnf install wimlib-utils parted dosfstools rsync ntfs-3g polkit libnotify
  ```
* **Arch Linux y derivados**:
  ```bash
  sudo pacman -S wimlib parted dosfstools rsync ntfs-3g polkit libnotify
  ```

---

## 🧪 Para Desarrolladores y Pruebas (Loopback)

Si deseas realizar pruebas de integración seguras sobre dispositivos de bloques virtuales (loopback) sin tocar hardware real:

1. Instala las dependencias de desarrollo:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
2. Ejecuta la suite de pruebas locales con privilegios root (requeridos para crear dispositivos loopback y formatear):
   ```bash
   sudo pytest tests/
   ```

---

## Licencia

Este proyecto está bajo la Licencia [MIT](LICENSE).
