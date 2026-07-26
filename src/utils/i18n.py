import gettext
import sys
import os
import locale

def setup_i18n():
    """
    Inicializa gettext para internacionalización de cadenas.
    Soporta entornos normales y empaquetados por PyInstaller (sys._MEIPASS).
    """
    domain = "memexicanisimos"
    
    # Resolver la ruta del directorio locale
    if getattr(sys, 'frozen', False):
        locale_dir = os.path.join(sys._MEIPASS, 'locale')
    else:
        # En desarrollo, resolver de forma relativa a src/
        locale_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'locale')

    # Detectar el idioma del sistema
    lang_code = "en"
    try:
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang:
            lang_code = sys_lang.split("_")[0]
    except Exception:
        pass
        
    # Fallback usando variables de entorno si getdefaultlocale falla
    if not lang_code or lang_code == "C":
        lang_env = os.environ.get("LANG", "en")
        lang_code = lang_env.split("_")[0] if lang_env else "en"

    try:
        translation = gettext.translation(domain, localedir=locale_dir, languages=[lang_code], fallback=True)
        translation.install()
        
        # Registrar _() de manera global en builtins
        import builtins
        builtins.__dict__['_'] = translation.gettext
        return translation.gettext
    except Exception:
        # Registrar fallback simple si hay errores
        import builtins
        builtins.__dict__['_'] = lambda s: s
        return lambda s: s
