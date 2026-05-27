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

## 2026-05-27 03:05:32 +02:00
- Sub-Phase: P4.6-5 Facial-Expression-Analyzer
- Commit-Hash: 301114d8682cec2c46977a07c2b57e9a7ac41fad
- Tests: 3793 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 16 passed targeted; synthetic 6 patterns; pair_001 multiple patterns detected
- Mini-Render: 30s probe Exitcode 0, render status in reports/phase4_6/p4_6_5/probe_clip/render_status.txt
- Visual-Check: reports/phase4_6/p4_6_5/probe_clip/still_010s.png
- Next: P4.6-6 Gameplay-vs-Menu Detection

## 2026-05-27 03:17:18 +02:00
- Sub-Phase: P4.6-6 Gameplay-vs-Menu Detection
- Commit-Hash: 1c6ba3cb9264184c16dd95154fb8691414192e08
- Tests: 3797 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 11 passed targeted; synthetic menu/gameplay tests; pair_001 timeline smoke
- Mini-Render: 30s probe Exitcode 0, duration 00:00:09.3247534
- Visual-Check: reports/phase4_6/p4_6_6/probe_clip/still_010s.png
- Next: P4.6-7 Smooth-Zoom-Engine

## 2026-05-27 03:25:46 +02:00
- Sub-Phase: P4.6-7 Smooth-Zoom-Engine
- Commit-Hash: 878846e712e1d7b4df9d5807ca7ba550d268b8b2
- Tests: 3806 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 14 passed targeted; easing, curve generation, hard-jump guard, pipeline regressions
- Mini-Render: 30s probe Exitcode 0, duration 00:00:09.4989419
- Visual-Check: reports/phase4_6/p4_6_7/probe_clip/still_010s.png
- Next: P4.6-8 Focus-Switch-Engine

## 2026-05-27 03:55:27 +02:00
- Sub-Phase: P4.6-8 Focus-Switch-Engine
- Commit-Hash: afe1c524573b301eb3ecae0f1da97ee6589f0e84
- Tests: 3813 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 18 passed targeted; decision tree, friend keywords, Ali yelling, decision_log.json
- Mini-Render: 30s probe Exitcode 0, duration 00:00:08.6175680
- Visual-Check: reports/phase4_6/p4_6_8/probe_clip/still_010s.png
- Next: P4.6-9-NEU Fingerprint-Erweiterung

## 2026-05-27 06:20:52 +02:00
- Sub-Phase: P4.6-9-NEU Fingerprint-Erweiterung
- Commit-Hash: 85b4d4667b4c8319c9b2b1188a7458bce601add4
- Tests: 3817 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 15 passed targeted; 40/40 fingerprint extension audit green
- Mini-Render: 30s probe Exitcode 0, duration 00:00:08.0708850
- Visual-Check: reports/phase4_6/p4_6_9/probe_clip/still_010s.png
- Next: P4.6-FINAL E2E + Abschlussbericht

## 2026-05-27 07:45:00 +02:00
- Sub-Phase: P4.6-FINAL E2E + Abschlussbericht
- Commit-Hash: 1cc0561f15735018ccf65985ccdd602a4852f46e
- Tests: 3818 passed, 2 skipped, 24 deselected (python -m pytest -x -q)
- Modul-Tests: 10 passed targeted duration-floor smoke after final guard-tolerance fix
- Full-Render: pair_001 Exitcode 0, duration 00:32:41.1312051, output exports/gaming_main/job_059053a7fa2a/job_059053a7fa2a_v1_final.mp4
- Visual-Check: reports/phase4_6/final/stills/*.png
- Final Status: PHASE 4.6 BEENDET MIT 0 SUB-PHASEN UEBERSPRUNGEN, ABER OFFENEN AKZEPTANZPUNKTEN
