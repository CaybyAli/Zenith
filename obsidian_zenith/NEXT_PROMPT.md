PROJECT ZENITH ? CONTROLLED MUSIC PREVIEW RUN ? STEP 21B/21C ? RENDER AFTER TAIL MUSIC COVERAGE FIX

ROLLE:
Du bist Bauchat/Engineer.
Ali f?hrt lokal aus.

STATUS:
- Phase 5: 100% DONE
- P5-L: 100% CLOSED
- Phase 5.5: 100% DONE
- Step 21A Code: DONE + pushed
- Current HEAD: 9c681eb fix(preview): build musicbed from timeline segments
- Step 20 Owner Review: FIX / NO-GO
- Render nach Step 21A noch NICHT gestartet
- Kein Upload
- Kein Runtime Learning
- Kein Qwen
- Kein Ingest

ZIEL:
Nur nach neuem Master-GO einen kontrollierten Render starten, um zu pr?fen:
- Musik l?uft bis Ende
- Kein Tail-Silence
- Musik nicht zu laut
- Musik bleibt unter Ali/Freunde-Stimme
- Source-Loudness-Automation greift
- Kein Upload

WICHTIGE ERWARTUNG:
- musicbed_command_segment_count == music_timeline_segment_count
- musicbed_command_matches_timeline=true
- tail_music_coverage_passed=true
- musicbed_no_silent_gaps=true
- owner review entscheidet final GO/NO-GO
