from __future__ import annotations

import re
import subprocess
from pathlib import Path


class AudioPeakDetector:
    """Findet genaue Audio-Peaks für reactive Zooms."""
    
    _FFMPEG = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
    _normalization_cache = {}  # Cache für Video-Normalisierung
    
    def detect_peaks(
        self,
        video_path: str,
        segment_start: float,
        segment_duration: float,
        threshold_db: float = -20.0,
        min_duration: float = 0.3,
        use_normalization: bool = True,
    ) -> list[dict]:
        """
        Findet genaue Audio-Peaks im Segment.
        
        Nutzt silencedetect INVERS: Alles was NICHT Stille ist = laut
        Mit optionaler adaptiver Normalisierung für verschiedene Video-Levels.
        """
        # ADAPTIVE NORMALISIERUNG
        if use_normalization:
            video_norm = self._get_video_normalization(video_path)
            threshold_db = self._normalize_threshold(threshold_db, video_norm)
        
        # silencedetect mit INVERSEM Threshold
        # Finde Stille, alles dazwischen = laut
        silence_threshold = -35  # Alles über -35dB = nicht-Stille
        
        cmd = [
            self._FFMPEG,
            "-ss", str(segment_start),
            "-t", str(segment_duration),
            "-i", video_path,
            "-af", f"silencedetect=noise={silence_threshold}dB:d=0.2",
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        # Parse silence_start und silence_end
        silence_periods = []
        
        for line in result.stderr.split("\n"):
            if "silence_start:" in line:
                match = re.search(r"silence_start:\s*([\d.]+)", line)
                if match:
                    silence_start = float(match.group(1))
                    silence_periods.append({"start": silence_start, "end": None})
            
            if "silence_end:" in line and silence_periods:
                match = re.search(r"silence_end:\s*([\d.]+)", line)
                if match:
                    silence_end = float(match.group(1))
                    if silence_periods[-1]["end"] is None:
                        silence_periods[-1]["end"] = silence_end
        
        # Konvertiere Stille zu lauten Momenten
        loud_periods = []
        
        # Erster lauter Moment: Von Segment-Start bis erste Stille
        if silence_periods and silence_periods[0]["start"] > 0:
            loud_periods.append({
                "start": segment_start,
                "end": segment_start + silence_periods[0]["start"]
            })
        elif not silence_periods:
            # Keine Stille = ganzes Segment laut
            loud_periods.append({
                "start": segment_start,
                "end": segment_start + segment_duration
            })
        
        # Laute Momente zwischen Stillen
        for i in range(len(silence_periods) - 1):
            if silence_periods[i]["end"] is not None:
                loud_start = segment_start + silence_periods[i]["end"]
                loud_end = segment_start + silence_periods[i + 1]["start"]
                
                if loud_end - loud_start >= min_duration:
                    loud_periods.append({
                        "start": loud_start,
                        "end": loud_end
                    })
        
        # Letzter lauter Moment: Von letzter Stille bis Segment-Ende
        if silence_periods and silence_periods[-1]["end"] is not None:
            loud_start = segment_start + silence_periods[-1]["end"]
            loud_end = segment_start + segment_duration
            
            if loud_end - loud_start >= min_duration:
                loud_periods.append({
                    "start": loud_start,
                    "end": loud_end
                })
        
        # JETZT: Für jeden lauten Moment, messe die TATSÄCHLICHE Lautstärke
        loud_peaks = []
        for loud in loud_periods:
            duration = loud["end"] - loud["start"]
            
            # volumedetect für DIESEN spezifischen Moment
            peak_db = self._measure_volume_for_period(
                video_path, loud["start"], duration
            )
            
            if peak_db is not None and peak_db > threshold_db:
                loud_peaks.append({
                    "start": loud["start"],
                    "end": loud["end"],
                    "peak_db": peak_db
                })
        
        print(f"[AUDIO-DEBUG] Raw peaks: {len(loud_peaks)}")
        
        # MERGE nahe Peaks
        merged_peaks = self._merge_close_peaks(loud_peaks, merge_gap=0.8)
        
        print(f"[AUDIO-DEBUG] After merging: {len(merged_peaks)} peaks")
        
        # HYSTERESIS: Erweitere Peaks ASYMMETRISCH (Reaktion, nicht Antizipation)
        hysteresis_peaks = self._apply_hysteresis(
            merged_peaks, 
            min_hold_time=1.0,    # Min. 1s Dauer
            extend_before=0.15,   # Nur 0.15s vor Peak
            extend_after=0.5      # 0.5s nach Peak
        )
        
        print(f"[AUDIO-DEBUG] After hysteresis: {len(hysteresis_peaks)} peaks")
        for i, peak in enumerate(hysteresis_peaks[:5], 1):
            duration = peak["end"] - peak["start"]
            print(f"[AUDIO-DEBUG]   Peak {i}: {peak['start']:.1f}s-{peak['end']:.1f}s ({duration:.1f}s, {peak['peak_db']:.1f}dB)")
        
        return hysteresis_peaks


    def _merge_close_peaks(self, peaks: list[dict], merge_gap: float = 0.8) -> list[dict]:
        """
        Merged Peaks die nah beieinander sind.
        
        Wenn zwei Peaks weniger als merge_gap Sekunden auseinander sind,
        werden sie zu einem Peak zusammengefasst.
        """
        if not peaks:
            return peaks
        
        # Sortiere nach Start-Zeit
        sorted_peaks = sorted(peaks, key=lambda p: p["start"])
        merged = [sorted_peaks[0].copy()]
        
        for peak in sorted_peaks[1:]:
            last_merged = merged[-1]
            gap = peak["start"] - last_merged["end"]
            
            if gap < merge_gap:
                # Merge: Erweitere den letzten Peak
                merged[-1]["end"] = peak["end"]
                merged[-1]["peak_db"] = max(merged[-1]["peak_db"], peak["peak_db"])
            else:
                # Neuer Peak
                merged.append(peak.copy())
        
        return merged


    def _apply_hysteresis(
        self, 
        peaks: list[dict], 
        min_hold_time: float = 1.0,       # Reduziert von 1.2s
        extend_before: float = 0.15,      # NEU: Nur 0.15s VOR dem Peak
        extend_after: float = 0.5         # NEU: 0.5s NACH dem Peak
    ) -> list[dict]:
        """
        Wendet Hysteresis an: Erweitert Peaks ASYMMETRISCH.
        
        Reaktion statt Antizipation: Zoom startet kurz vor/mit dem lauten Moment,
        bleibt aber danach länger aktiv für weniger Flackern.
        
        Args:
            min_hold_time: Minimale Dauer eines Zooms (1.0s)
            extend_before: Wie viel VOR dem Peak erweitern (0.15s)
            extend_after: Wie viel NACH dem Peak erweitern (0.5s)
        """
        if not peaks:
            return peaks
        
        extended = []
        
        for peak in peaks:
            duration = peak["end"] - peak["start"]
            
            # ASYMMETRISCHE Extension: weniger vor, mehr nach
            new_start = peak["start"] - extend_before
            new_end = peak["end"] + extend_after
            
            # Falls immer noch zu kurz → erweitere HAUPTSÄCHLICH nach hinten
            if (new_end - new_start) < min_hold_time:
                missing = min_hold_time - (new_end - new_start)
                # 20% vor, 80% nach
                new_start -= missing * 0.2
                new_end += missing * 0.8
            
            extended.append({
                "start": max(new_start, peak["start"] - 0.5),  # Max 0.5s vor Original
                "end": new_end,
                "peak_db": peak["peak_db"]
            })
        
        # Merge wieder (erweiterte Peaks können jetzt überlappen)
        return self._merge_close_peaks(extended, merge_gap=0.3)


    def _get_video_normalization(self, video_path: str) -> dict:
        """
        Analysiert das GESAMTE Video einmalig und cached die Normalisierungs-Werte.
        
        Returns:
            {"mean_volume": -18.5, "max_volume": -6.2, "dynamic_range": 12.3}
        """
        # Check cache
        if video_path in self._normalization_cache:
            return self._normalization_cache[video_path]
        
        print(f"[AUDIO-NORM] Analyzing entire video for normalization...")
        
        cmd = [
            self._FFMPEG,
            "-i", video_path,
            "-af", "volumedetect",
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        mean_volume = None
        max_volume = None
        
        for line in result.stderr.split("\n"):
            if "mean_volume:" in line:
                match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", line)
                if match:
                    mean_volume = float(match.group(1))
            if "max_volume:" in line:
                match = re.search(r"max_volume:\s*([-\d.]+)\s*dB", line)
                if match:
                    max_volume = float(match.group(1))
        
        if mean_volume is None or max_volume is None:
            # Fallback
            normalization = {"mean_volume": -20.0, "max_volume": -6.0, "dynamic_range": 14.0}
        else:
            dynamic_range = max_volume - mean_volume
            normalization = {
                "mean_volume": mean_volume,
                "max_volume": max_volume,
                "dynamic_range": dynamic_range
            }
        
        # Cache
        self._normalization_cache[video_path] = normalization
        
        print(f"[AUDIO-NORM] Video baseline: mean={normalization['mean_volume']:.1f}dB, "
              f"max={normalization['max_volume']:.1f}dB, range={normalization['dynamic_range']:.1f}dB")
        
        return normalization
    
    def _normalize_threshold(self, base_threshold: float, video_norm: dict) -> float:
        """
        Passt Threshold basierend auf Video-Normalisierung an.
        
        Beispiel:
        - Leises Video (mean=-25dB) → Threshold wird angehoben (-18dB)
        - Lautes Video (mean=-15dB) → Threshold wird gesenkt (-22dB)
        """
        video_mean = video_norm["mean_volume"]
        
        # Offset: Wie viel lauter/leiser ist das Video vs. Standard (-20dB)
        offset = video_mean - (-20.0)
        
        # Passe Threshold an (invertiert: leiser = höherer Threshold)
        adjusted = base_threshold - offset
        
        print(f"[AUDIO-NORM] Threshold {base_threshold:.1f}dB → {adjusted:.1f}dB (offset={offset:.1f}dB)")
        
        return adjusted


    def _measure_volume_for_period(
        self,
        video_path: str,
        start: float,
        duration: float
    ) -> float | None:
        """Misst mean_volume für einen spezifischen Zeitraum."""
        cmd = [
            self._FFMPEG,
            "-ss", str(start),
            "-t", str(duration),
            "-i", video_path,
            "-af", "volumedetect",
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        for line in result.stderr.split("\n"):
            if "mean_volume:" in line:
                match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", line)
                if match:
                    return float(match.group(1))
        
        return None