# Learning Run Log - P5-L

Stand: 2026-06-05

## Laufstatus

- Noch kein Learning-Run gestartet
- Noch kein Overnight gestartet
- Noch kein Dauerlernen gestartet
- Noch kein Qwen-Autocut gestartet
- Noch kein Ingest gestartet
- Noch kein Render gestartet
- Noch keine Musik gestartet

## Hinweis

Erste echte Eintraege kommen erst nach P5-L2 oder P5-L5.

P5-L0 ist nur Dokumentation.

## P5-L2 Mini-Run — Analysis-only

- Modus: analysis_only_dry_run
- Status: ok
- Report-Pfad: reports/p5_l2_analysis_only_dry_run/p5_l2_analysis_report.json
- Summary-Pfad: reports/p5_l2_analysis_only_dry_run/p5_l2_analysis_summary.md
- Kein Render
- Kein Qwen
- Kein Ingest
- Keine Musik
- Kein Loop
- Phase 5.5 nicht benutzt
- deleted_files: []

## P5-L3 Mini-Run Safe Write

- Zeitpunkt: 2026-06-05 23:32:16
- Status: ok
- Modus: style_memory_safe_write
- memory_write_target: reports_only_candidate
- Outputs:
  - reports/p5_l3_style_memory_safe_write/style_memory_candidate.json
  - reports/p5_l3_style_memory_safe_write/style_memory_manifest.json
  - reports/p5_l3_style_memory_safe_write/style_memory_summary.md
- Counts:
  - pair_fingerprints: 20
  - top_solo_fingerprints: 30
  - vlog_fingerprints: 3
  - pair_truth_entries: 20
- forbidden_inputs_used: []
- warnings: []
- deleted_files: []
- qwen_used: false
- render_used: false
- ingest_used: false
- music_used: false
- autocut_used: false
- overnight_started: false
- learning_loop_started: false
- phase_5_5_used: false

---
## 2026-06-05 — P5-L4 Analysis-only Evaluator Run

Run-Art:
- Qwen Analysis-only Evaluator
- kein Render
- kein Ingest
- keine Musik
- kein Autocut
- kein Overnight
- kein echter Learning-Loop
- kein Phase 5.5

Ergebnis:
- Mini-run ohne Qwen: status=ok
- Local-Qwen Smoke: sauber geskippt wegen Import-Kontext
- Kein Fake-Erfolg
- qwen_can_cut=false
- qwen_autocut_allowed=false

Report-Pfade:
- reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_report.json
- reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_manifest.json
- reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_summary.md

## 2026-06-05 — P5-L5 Overnight Dry-run Mini-run

Run:
- script: scripts/p5_l5_overnight_dry_run.py
- mode: overnight_dry_run
- dry_run_only=true
- max_items=5
- status=ok
- items_planned=5
- items_processed=5
- stop_file_supported=true
- stop_file_detected=false

Reports:
- reports/p5_l5_overnight_dry_run/overnight_dry_run_plan.json
- reports/p5_l5_overnight_dry_run/overnight_dry_run_manifest.json
- reports/p5_l5_overnight_dry_run/overnight_dry_run_summary.md

Safety:
- real_overnight_started=false
- overnight_started=false
- qwen_used=false
- qwen_autocut_used=false
- render_used=false
- ingest_used=false
- music_used=false
- autocut_used=false
- learning_loop_started=false
- phase_5_5_used=false
- deleted_files=[]
