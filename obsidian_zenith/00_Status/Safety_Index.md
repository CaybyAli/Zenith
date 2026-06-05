# SAFETY INDEX

Stand: 2026-06-06

## Zentrale Safety-Regeln

- Kein Render in P5-L6.5.
- Kein Preview-Render in P5-L6.5.
- Kein Ingest in P5-L6.5.
- Keine Musik.
- Keine Phase 5.5.
- Kein echter Learning-Loop.
- Kein echter Overnight-Dauerlauf.
- Kein Qwen-Autocut.
- Qwen bleibt `analysis_only`.
- Qwen bleibt `can_cut=false`.
- Reports bleiben untracked.
- Keine Produktionsdateien ueberschreiben.
- Keine `video_configs` oder `learning_corpus` Writes ohne eigenes Gate.
- Keine Datei-Loeschung ohne ausdrueckliche Erlaubnis.
- Echte Loop-Starts nur mit Master-GO, Enable-Flag, Stop-Schalter, Timeout und Manifest.

## Git-Regeln

- Nie `git add .`.
- Nie `git add -A`.
- Keine Reports committen, ausser Master erlaubt es explizit.
- Nur explizit erlaubten Scope stagen.
- Bestehende untracked Altlasten nicht anfassen.

## Aktueller Gate

Naechster Gate: P5-L6.5 Gruppe 5E - Abschlussbericht / Final Audit, nur nach Master-GO.

P5-L7 und Phase 5.5 bleiben gesperrt.

## 5D Qwen Kontrollrun Ergebnis

- Modell: `qwen3.6:latest`.
- `qwen_used=true`.
- `qwen_visible_response=true`.
- `qwen_role=analysis_only`.
- `qwen_can_cut=false`.
- `qwen_autocut_allowed=false`.
- `dangerous_response_detected=false`.
- `render_used=false`.
- `ingest_used=false`.
- `music_used=false`.
- `autocut_used=false`.
- `learning_loop_started=false`.
- `phase_5_5_used=false`.
