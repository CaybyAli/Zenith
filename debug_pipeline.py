from pathlib import Path
from core.edit_signal_extractor import EditSignalExtractor
from core.highlight_selector import HighlightSelector

# DEIN TEST-VIDEO
VIDEO_PATH = "inbox/gaming_main/Rocket League Neuer Test37.mp4"

# Fake minimal Job
class FakeJob:
    def __init__(self):
        self.job_id = "debug_test"
        self.raw_video_path = VIDEO_PATH

class FakeAnalysis:
    def __init__(self, duration):
        self.job_id = "debug_test"
        self.duration_seconds = duration
        self.file_size_bytes = 100000
        self.usable_for_shorts = True
        self.usable_for_longform = True
        self.analysis_confidence = 0.8
        self.notes = []

# 1. VIDEO DURATION
from moviepy import VideoFileClip
with VideoFileClip(VIDEO_PATH) as clip:
    duration = clip.duration

print("="*60)
print(f"VIDEO: {duration:.1f}s ({duration/60:.1f} min)")
print(f"TARGET: {duration * 0.95:.1f}s (95% retention)")
print("="*60)

job = FakeJob()
analysis = FakeAnalysis(duration)

# 2. EXTRACT SIGNALS
print("\n🔍 EXTRACTING SIGNALS...")
extractor = EditSignalExtractor()
signals = extractor.extract(job, analysis)

audio_peaks = [s for s in signals if s.signal_type == "audio_peak"]
motion_peaks = [s for s in signals if s.signal_type == "motion_peak"]

print(f"✅ Total signals: {len(signals)}")
print(f"   📢 audio_peak: {len(audio_peaks)}")
print(f"   🎮 motion_peak: {len(motion_peaks)}")

# 3. SELECT HIGHLIGHTS
print("\n🎯 SELECTING HIGHLIGHTS...")
selector = HighlightSelector()
result = selector.select(job, analysis, signals)

highlights = result["highlight_candidates"]

print(f"✅ Highlight candidates: {len(highlights)}")

if highlights:
    scores = [h.highlight_score for h in highlights]
    print(f"   Score range: {min(scores):.2f} - {max(scores):.2f}")
    
    # Zeige die ersten 15
    print("\n📋 FIRST 15 HIGHLIGHTS:")
    for i, h in enumerate(highlights[:15]):
        print(f"   {i+1:2d}. {h.start_time:6.1f}s-{h.end_time:6.1f}s "
              f"({h.end_time-h.start_time:4.1f}s) score={h.highlight_score:.2f}")
    
    if len(highlights) > 15:
        print(f"   ... and {len(highlights)-15} more")
else:
    print("❌ NO HIGHLIGHTS!")

print("\n" + "="*60)
print(f"ERGEBNIS: {len(highlights)} Highlights gefunden")
print(f"ERWARTET: 40-50+ Highlights")
print("="*60)