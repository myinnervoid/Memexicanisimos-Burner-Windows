"""Módulo de internacionalización (i18n) para la aplicación."""
import gettext
import sys
import os
import locale
import builtins

def setup_i18n():
    """
    Inicializa gettext para internacionalización de cadenas.
    Soporta entornos normales y empaquetados por PyInstaller.
    """
    domain = "memexicanisimos"

    if getattr(sys, 'frozen', False):
        # pylint: disable=protected-access
        locale_dir = os.path.join(sys._MEIPASS, 'locale')
    else:
        locale_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'locale'
        )

    lang_code = "en"
    try:
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang:
            lang_code = sys_lang.split("_")[0]
    except (ValueError, locale.Error):
        pass

    if not lang_code or lang_code == "C":
        lang_env = os.environ.get("LANG", "en")
        lang_code = lang_env.split("_")[0] if lang_env else "en"

    try:
        translation = gettext.translation(
            domain, localedir=locale_dir, languages=[lang_code], fallback=True
        )
        translation.install()

        builtins.__dict__['_'] = translation.gettext
        return translation.gettext
    except OSError:
        builtins.__dict__['_'] = lambda s: s
        return lambda s: s
