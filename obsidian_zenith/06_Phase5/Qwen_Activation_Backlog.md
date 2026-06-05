# QWEN ACTIVATION BACKLOG

## Ziel

Qwen/LLMBrain soll lokal als Analyse-Neben-Track laufen.

## Muss beweisen

- Server erreichbar
- Modell erreichbar
- JSON-Antwort stabil
- kein stiller Fallback
- keine Schnittentscheidung
- kein Render
- kein Ingest

## Status

Noch offen.

## Update 2026-06-05 — K8 DONE

Status:
DONE

Beweis:
- LocalQwenSideTrack gebaut.
- Mock Tests: 7 passed.
- Real-Adapter-Smoke gegen lokales Ollama grün.
- qwen3.6:latest vorhanden.
- JSON parsebar.
- role=analysis_only.
- can_cut=false.
- Kein Qwen-Auto-Schnitt.

Code Commit:
c549586 feat(P5-K8): add local Qwen side-track adapter

Grenze:
Qwen bleibt Side-Track und darf nicht automatisch schneiden.
