import os
import pytest
import sys
from src.cli import validate_environment

def test_validate_environment_not_root(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    args = type('Args', (object,), {"iso": "test.iso", "device": "/dev/sdb"})()
    with pytest.raises(SystemExit) as exc:
        validate_environment(args)
    assert exc.value.code == 1

def test_validate_environment_invalid_iso(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    args = type('Args', (object,), {"iso": "test.iso", "device": "/dev/sdb"})()
    with pytest.raises(SystemExit) as exc:
        validate_environment(args)
    assert exc.value.code == 1

def test_validate_environment_invalid_device(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    args = type('Args', (object,), {"iso": "test.iso", "device": "sdb"})()
    with pytest.raises(SystemExit) as exc:
        validate_environment(args)
    assert exc.value.code == 1
import os
