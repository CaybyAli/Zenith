# PROJECT ZENITH — PHASE 1 CLEANUP LIST

## Baseline
Start-HEAD: cd2792a
Tests: 3481 passed, 2 skipped, 0 failed

## A) Zum Verschieben
- Root test_*.py Dateien -> tests/
- Analyse-Dokumente *.md im Root -> docs/archive/
- reset_jobs.py und reset_all_jobs.py -> scripts/

## B) Zum Löschen — nur nach Bestätigung
- _audit_*.txt
- _patch_*.py
- _verify_*.txt
- _verify_*.json
- _verify_*.py
- models/jarvis_*.py nur falls nicht importiert

## C) Behalten / Unklar
- BUG_DIAGNOSIS.md -> eher docs/archive/
- PROJECT_INVENTORY.md -> eher docs/archive/
- ZENITH_PHASE_2B_PRO_ANALYSIS.md -> eher docs/archive/
- assets/sfx/censor/censor_sfx_manifest.json behalten
- .gitignore später erweitern

## STOPP
Diese Liste ist nur zur Prüfung.
Noch nichts löschen.
Noch nichts verschieben.
Cleanup-Ausführung erst in Unterphase 1.5 nach Bestätigung.
