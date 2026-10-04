import os
import sys
import builtins
import gettext
from src.utils.i18n import setup_i18n

def test_setup_i18n_default(monkeypatch):
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _ = setup_i18n()
    assert "_" in builtins.__dict__
    assert callable(_)

def test_setup_i18n_fallback(monkeypatch):
    monkeypatch.setenv("LANG", "invalid_LANG")
    # Intentional failure to test fallback
    monkeypatch.setattr(gettext, "translation", lambda *args, **kwargs: (_ for _ in ()).throw(OSError))
    _ = setup_i18n()
    assert callable(_)
    assert _("Testing fallback") == "Testing fallback"
