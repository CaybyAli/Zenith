# P4.6-4 Face-Detection-Diagnose

## Bestehende Architektur

- `core/face_reaction_analyzer.py` nutzt OpenCV Haar-Cascade (`haarcascade_frontalface_default.xml`) als Proxy.
- Der bisherige Pfad erzeugt Face-Reaction-Punkte ohne Landmark-Semantik.
- `core/facecam_reaction_analyzer.py` misst nur Frame-Signature-Deltas in einem Facecam-Crop und erkennt keine Gesichter.
- Es gab vor P4.6-4 kein MediaPipe-Modul und keine Landmark-Ausgabe fuer Expressions.

## Problem

Haar-Cascade ist fuer OBS-Facecam, seitliche Kopfhaltung, Hand-vor-Mund und schnelle Reaktionen instabil. Fuer P4.6-5 werden echte Landmarks benoetigt.

## Migration

- Neues Modul: `core/face_detector_mediapipe.py`
- Backend: lokales `mediapipe` Face Mesh, `refine_landmarks=True`, `max_num_faces=1`
- Default-ROI: rechte Haelfte des 32:9 OBS-Composites, passend zur aktuellen Korpusbeschreibung.
- Output:
  - `FaceDetectionPoint(timestamp, detected, landmarks)`
  - `FaceLandmarks(landmarks, bounding_box, confidence)`
- Pipeline-Anbindung:
  - `gaming_pipeline` fuehrt MediaPipe-Face-Detection defensiv nach Voice-Intensity aus.
  - Fehler blockieren Render nicht; sie werden als `FACE_DETECTION skipped` geloggt.

## Lokale Installation

`mediapipe==0.10.35` wurde lokal installiert. Keine Cloud-API, kein Google-Service.
