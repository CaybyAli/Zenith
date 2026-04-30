import sys
from core.edit_signal_extractor import EditSignalExtractor

# Zeige wo das Modul geladen wird
print("Module loaded from:", EditSignalExtractor.__module__)
print("File location:", sys.modules['core.edit_signal_extractor'].__file__)

# Zeige den step_size Wert
extractor = EditSignalExtractor()
print("\nTesting step_size in code...")
# Wir müssen in den Source-Code schauen
import inspect
source = inspect.getsource(extractor._extract_audio_energy_signals)
if "step_size: float = 1.0" in source:
    print("✅ USING AGGRESSIVE VERSION (step_size = 1.0)")
elif "step_size: float = 2.0" in source:
    print("❌ USING OLD VERSION (step_size = 2.0)")
else:
    print("❓ UNKNOWN VERSION")