import os
import subprocess
import shutil
from src.utils.notifications import send_notification

def test_send_notification_notify_send(monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", lambda x: "some/path" if x == "notify-send" else None)

    called_args = []
    def fake_run(args, check):
        called_args.extend(args)

    monkeypatch.setattr(subprocess, "run", fake_run)
    send_notification("Test Title", "Test Body")

    assert "notify-send" in called_args
    assert "Test Title" in called_args
    assert "Test Body" in called_args

def test_send_notification_fallback_print(monkeypatch, capsys):
    monkeypatch.setattr(shutil, "which", lambda x: None)
    monkeypatch.delenv("DISPLAY", raising=False)

    send_notification("Test Title", "Test Body", "critical")

    captured = capsys.readouterr()
    assert "NOTIFICACIÓN [CRITICAL]: Test Title - Test Body" in captured.out
