import os
import pytest
import time
import threading
from src.core.burner_core import BurnerEngine

@pytest.mark.skipif(os.geteuid() != 0, reason="Estas pruebas requieren privilegios root (sudo).")
def test_successful_burn(fake_iso, loopback_device):
    """Prueba el flujo completo exitoso, incluyendo división wimsplit."""
    engine = BurnerEngine(fake_iso, loopback_device)
    
    phases = []
    def progress_callback(phase, val):
        phases.append(phase)
        
    def log_callback(msg):
        pass
        
    engine.execute(progress_callback, log_callback)
    
    # Verificar que completó todas las fases y llegó al final
    assert "Completado" in phases
    assert len(phases) > 3

@pytest.mark.skipif(os.geteuid() != 0, reason="Estas pruebas requieren privilegios root (sudo).")
def test_cancel_before_start(fake_iso, loopback_device):
    """Prueba que el motor cancele inmediatamente al indicárselo antes de ejecutar."""
    engine = BurnerEngine(fake_iso, loopback_device)
    engine.cancel()
    
    def progress_callback(phase, val):
        pass
    def log_callback(msg):
        pass
        
    with pytest.raises(Exception, match="Operación cancelada"):
        engine.execute(progress_callback, log_callback)

@pytest.mark.skipif(os.geteuid() != 0, reason="Estas pruebas requieren privilegios root (sudo).")
def test_cancel_during_wimsplit(fake_iso, loopback_device):
    """Prueba la cancelación del motor durante la ejecución de wimsplit (Mejora 4)."""
    engine = BurnerEngine(fake_iso, loopback_device)
    
    def progress_callback(phase, val):
        # Cancelar cuando se llegue a la fase de wimsplit
        if "Dividiendo" in phase:
            # Cancelar en un hilo separado para simular acción de usuario en GUI
            threading.Thread(target=engine.cancel).start()
            
    def log_callback(msg):
        pass
        
    with pytest.raises(Exception, match="Operación cancelada"):
        engine.execute(progress_callback, log_callback)

@pytest.mark.skipif(os.geteuid() != 0, reason="Estas pruebas requieren privilegios root (sudo).")
def test_insufficient_space(fake_iso, loopback_device):
    """Prueba que falle con excepción de espacio si la ISO excede el tamaño del disco."""
    # Intentar quemar en una partición inexistente de menor tamaño o simular
    engine = BurnerEngine(fake_iso, loopback_device)
    
    # Modificar artificialmente el tamaño de la ISO para exceder los 8GB
    # (Mockear os.path.getsize para que retorne 12GB)
    original_getsize = os.path.getsize
    try:
        os.path.getsize = lambda path: 12 * 1024 * 1024 * 1024 if path == fake_iso else original_getsize(path)
        
        def progress_callback(phase, val):
            pass
        def log_callback(msg):
            pass
            
        with pytest.raises(Exception, match="La memoria USB no cuenta con espacio suficiente"):
            engine.execute(progress_callback, log_callback)
    finally:
        os.path.getsize = original_getsize

@pytest.mark.skipif(os.geteuid() != 0, reason="Estas pruebas requieren privilegios root (sudo).")
def test_invalid_device(fake_iso):
    """Prueba que el motor arroje un error claro si el dispositivo de bloque no es válido."""
    engine = BurnerEngine(fake_iso, "/dev/dispositivo_no_existente_xyz")
    
    def progress_callback(phase, val):
        pass
    def log_callback(msg):
        pass
        
    with pytest.raises(Exception):
        engine.execute(progress_callback, log_callback)
