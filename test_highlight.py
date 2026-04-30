import sys
import inspect
from core.highlight_selector import HighlightSelector

selector = HighlightSelector()
source = inspect.getsource(selector._score_highlight_window)

print("=== HIGHLIGHT SELECTOR VERSION CHECK ===\n")

if "score += 0.18" in source and "audio_activity" in source:
    print("✅ USING OPTIMIZED VERSION")
    print("   audio_activity: 0.12 → 0.18")
    print("   motion_activity: 0.10 → 0.15")
elif "score += 0.12" in source and "audio_activity" in source:
    print("❌ USING OLD VERSION")
    print("   audio_activity: still 0.12 (should be 0.18!)")
else:
    print("❓ UNKNOWN VERSION")

print("\n=== THRESHOLD CHECK ===\n")

source2 = inspect.getsource(selector.select)
if "if highlight_score >= 0.38:" in source2:
    print("✅ Threshold: 0.38 (OPTIMIZED)")
elif "if highlight_score >= 0.45:" in source2:
    print("❌ Threshold: 0.45 (OLD)")
else:
    print("❓ Unknown threshold")