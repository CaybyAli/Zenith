# SCRIPT INDEX

Stand: 2026-06-06

## Zweck

Diese Datei gibt neuen Chats eine schnelle Orientierung ueber die aktuellen P5-L Scripts. Sie ist Dokumentation, kein Ausfuehrungsauftrag.

## Scripts

| Datei | Zweck | Input | Output | Safety | Status |
|---|---|---|---|---|---|
| `scripts/p5_l2_analysis_only_dry_run.py` | Analysiert vorhandene Style-DNA, Pair Truth und Fingerprints ohne Ausfuehrung. | `video_configs/*style_dna.json`, `video_configs/pair_track_truth.json`, `learning_corpus/*/style_fingerprint.json` | `reports/p5_l2_analysis_only_dry_run/` | Kein Qwen, kein Render, kein Ingest, kein Loop; Output hart begrenzt. | DONE |
| `scripts/p5_l3_style_memory_safe_write.py` | Baut einen reports-only Style-Memory Candidate. | P5-L2 Report und Style-DNA Reports. | `reports/p5_l3_style_memory_safe_write/` | Keine Produktionsdateien, keine `video_configs`, kein `learning_corpus` Write. | DONE |
| `scripts/p5_l4_qwen_analysis_only_evaluator.py` | Bewertet P5-L3 Candidate mit Qwen-Analyse-Regeln. | P5-L3 Candidate/Manifest, optional P5-L2 Report. | `reports/p5_l4_qwen_analysis_only_evaluator/` | Qwen nur lokal, `analysis_only`, `can_cut=false`, external URL blockiert. | DONE |
| `scripts/p5_l5_overnight_dry_run.py` | Plant begrenzten Overnight-Dry-run ohne echten Dauerlauf. | P5-L2 bis P5-L4 Reports. | `reports/p5_l5_overnight_dry_run/` | `dry_run_only=true`, `max_items=5`, Stop-file support, kein echter Loop. | DONE |
| `scripts/p5_l6_owner_review_quality_gate.py` | Baut Owner Review Packet/Manifest und Quality Gate. | P5-L2 bis P5-L5 Reports. | `reports/p5_l6_owner_review_quality_gate/` | Qwen optional/lokal, `analysis_only`, `can_cut=false`, Owner-GO nur explizit. | DONE |
| `core/qwen_side_track.py` | Lokaler Qwen Side-Track Adapter. | Prompt an lokales Ollama `localhost`/`127.0.0.1`. | Strukturierte JSON-Analyse. | Externe Hosts blockiert, strict JSON, `analysis_only`, `can_cut=false`. | DONE |

## Aktuelle Regel

In P5-L6.5 5C wird nichts davon ausgefuehrt. Naechster moeglicher technischer Schritt ist 5D Qwen Kontrollrun nach Master-GO.
