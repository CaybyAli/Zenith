## 2026-05-27 02:37:58 +02:00
- Sub-Phase: P4.6-2 Speaker-Identifikation Hybrid
- Commit-Hash: e8cad1e0126bfbe4f3b4419603f5c9dcddea0af8
- Tests: 3778 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 37 passed, plus targeted E2E regression 7 passed
- Mini-Render: 00:00:09.4868693 for 30s probe, Exitcode 0
- Visual-Check: reports/phase4_6/p4_6_2/probe_clip/still_005s.png
- Next: P4.6-3 Voice-Intensity-Analyzer

## 2026-05-27 02:46:21 +02:00
- Sub-Phase: P4.6-3 Voice-Intensity-Analyzer
- Commit-Hash: dca57a121989c1b7d9313d4a4cc953269449aebc
- Tests: 3783 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 12 passed targeted, pair_001 distribution normal=62.06%, leise_erhoeht=23.713%, schreien=11.382%, bruellen=2.846%
- Mini-Render: 30s probe Exitcode 0, render status in reports/phase4_6/p4_6_3/probe_clip/render_status.txt
- Visual-Check: reports/phase4_6/p4_6_3/probe_clip/still_008s.png
- Next: P4.6-4 Face-Detection-Stabilisierung

## 2026-05-27 02:57:00 +02:00
- Sub-Phase: P4.6-4 Face-Detection MediaPipe
- Commit-Hash: 48a36bc4430c5f74640d4e57380cd8f16d5d70da
- Tests: 3786 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 8 passed targeted; pair_001 30-sample detection rate 100.0% with 478 landmarks
- Mini-Render: 30s probe Exitcode 0, render status in reports/phase4_6/p4_6_4/probe_clip/render_status.txt
- Visual-Check: reports/phase4_6/p4_6_4/probe_clip/still_010s.png
- Next: P4.6-5 Facial-Expression-Analyzer

