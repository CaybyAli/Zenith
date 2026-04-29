# core/thumbnail_generator.py
"""
Intelligenter Thumbnail-Generator für Zenith Pipeline
Wählt besten Frame basierend auf Quality-Score (Kontrast, Action, Details)
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List
import logging
import sys

# Logging-Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Intelligenter Thumbnail-Generator mit Quality-Score-System"""
    
    def __init__(self):
        self.skip_start_percent = 0.05  # Vermeide erste 5% (Fade-In)
        self.skip_end_percent = 0.05    # Vermeide letzte 5% (Fade-Out)
        self.candidate_positions = [0.25, 0.40, 0.60, 0.75]  # Sample-Positionen
    
    def calculate_frame_quality_score(self, frame: np.ndarray) -> float:
        """
        Berechnet Quality-Score für einen Frame basierend auf:
        - Farb-Varianz (Kontrast)
        - Helligkeits-Verteilung
        - Edge-Dichte (Details)
        
        Returns:
            float: Quality-Score (höher = besser)
        """
        # 1. Farb-Varianz (Standardabweichung über alle Kanäle)
        color_variance = np.std(frame)
        
        # 2. Helligkeits-Verteilung (vermeide zu dunkle/helle Frames)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness_mean = np.mean(gray)
        brightness_penalty = abs(brightness_mean - 127.5) / 127.5  # 0 = optimal (mittlere Helligkeit)
        
        # 3. Edge-Dichte (Details/Action)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # 4. Vermeide schwarze/weiße Frames
        black_pixel_ratio = np.sum(gray < 20) / gray.size
        white_pixel_ratio = np.sum(gray > 235) / gray.size
        fade_penalty = max(black_pixel_ratio, white_pixel_ratio)
        
        # Kombinierter Score (gewichtet)
        score = (
            color_variance * 1.5 +           # Hoher Kontrast wichtig
            edge_density * 200.0 -           # Details/Action wichtig
            brightness_penalty * 50.0 -      # Zu dunkel/hell vermeiden
            fade_penalty * 300.0             # Schwarze/weiße Frames stark strafen
        )
        
        logger.debug(f"Frame Quality - Variance: {color_variance:.2f}, "
                    f"Edges: {edge_density:.4f}, Brightness: {brightness_mean:.1f}, "
                    f"Fade: {fade_penalty:.4f}, Score: {score:.2f}")
        
        return score
    
    def extract_best_frame(
        self, 
        video_path: Path, 
        output_path: Path,
        width: int = 1280,
        height: int = 720
    ) -> bool:
        """
        Extrahiert besten Frame basierend auf Quality-Score
        
        Args:
            video_path: Pfad zum Video
            output_path: Pfad für Thumbnail-Output (z.B. thumbnail.jpg)
            width: Thumbnail-Breite
            height: Thumbnail-Höhe
        
        Returns:
            bool: True bei Erfolg
        """
        try:
            logger.info(f"🎬 Analysiere Video: {video_path}")
            
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"❌ Konnte Video nicht öffnen: {video_path}")
                return False
            
            # Video-Metadaten
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📊 Video-Info: {total_frames} Frames, {fps:.2f} FPS, {duration:.1f}s")
            
            # Sichere Zone (vermeide Fade-In/Out)
            safe_start_frame = int(total_frames * self.skip_start_percent)
            safe_end_frame = int(total_frames * (1 - self.skip_end_percent))
            
            logger.info(f"🎯 Sichere Zone: Frame {safe_start_frame} - {safe_end_frame} ({self.skip_start_percent*100:.0f}% - {(1-self.skip_end_percent)*100:.0f}%)")
            
            # Kandidaten-Frames
            candidate_frames: List[Tuple[int, float, np.ndarray]] = []
            
            for position in self.candidate_positions:
                frame_number = int(safe_start_frame + (safe_end_frame - safe_start_frame) * position)
                
                # Frame extrahieren
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    logger.warning(f"⚠️  Konnte Frame {frame_number} nicht lesen")
                    continue
                
                # Quality-Score berechnen
                score = self.calculate_frame_quality_score(frame)
                candidate_frames.append((frame_number, score, frame))
                
                timestamp = frame_number / fps if fps > 0 else 0
                logger.info(f"📸 Kandidat @ {position*100:.0f}% (Frame {frame_number}, {timestamp:.1f}s): Score {score:.2f}")
            
            cap.release()
            
            if not candidate_frames:
                logger.error("❌ Keine gültigen Kandidaten-Frames gefunden")
                return False
            
            # Besten Frame wählen
            best_frame_number, best_score, best_frame = max(candidate_frames, key=lambda x: x[1])
            best_timestamp = best_frame_number / fps if fps > 0 else 0
            
            logger.info(f"✅ Bester Frame: #{best_frame_number} @ {best_timestamp:.1f}s (Score: {best_score:.2f})")
            
            # Output-Verzeichnis erstellen falls nötig
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Thumbnail speichern (hochwertig)
            resized = cv2.resize(best_frame, (width, height), interpolation=cv2.INTER_LANCZOS4)
            cv2.imwrite(
                str(output_path), 
                resized, 
                [cv2.IMWRITE_JPEG_QUALITY, 95]  # Hohe JPEG-Qualität
            )
            
            file_size = output_path.stat().st_size / 1024  # KB
            logger.info(f"💾 Thumbnail gespeichert: {output_path} ({file_size:.1f} KB)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Thumbnail-Generierung: {e}", exc_info=True)
            return False


# Standalone-Funktion für Legacy-Kompatibilität
def generate_thumbnail(video_path: Path, output_path: Path, **kwargs) -> bool:
    """Legacy-Wrapper für bestehende Pipeline"""
    generator = ThumbnailGenerator()
    return generator.extract_best_frame(video_path, output_path, **kwargs)


# CLI-Support
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m core.thumbnail_generator <video_path> <output_path> [width] [height]")
        print("Example: python -m core.thumbnail_generator video.mp4 thumbnail.jpg 1280 720")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    
    if not video_path.exists():
        logger.error(f"❌ Video nicht gefunden: {video_path}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎨 ZENITH THUMBNAIL GENERATOR - Phase 2.3")
    logger.info("=" * 60)
    
    generator = ThumbnailGenerator()
    success = generator.extract_best_frame(video_path, output_path, width, height)
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ THUMBNAIL ERFOLGREICH GENERIERT")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ THUMBNAIL-GENERIERUNG FEHLGESCHLAGEN")
        logger.error("=" * 60)
        sys.exit(1)