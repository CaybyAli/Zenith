PROJECT ZENITH ? CONTROLLED MUSIC PREVIEW RUN ? STEP 24A ? DIAGNOSE OWNER-FIX AFTER BACKGROUND MUSIC MIX FIX

ROLE:
Bauchat/Engineer.
Ali executes locally.
Diagnosis only.
No blind patch.
No render.
No upload.
No runtime learning.
No Qwen.
No ingest.

Current HEAD:
0867e32f97d61883e12cbe8fa9d7360e33aa24e2
docs(obsidian): record render after background music mix fix

Latest reviewed render:
reports/controlled_music_preview_run/step13_visual_proper_run_music_render/run_20260612_004039/controlled_music_preview_main.mp4

Owner Review Step 24:
FIX / NO-GO.
Ali says the same audible errors are still present as before.

Known owner symptoms:
- Music still not properly in background / still too dominant.
- New song starts still feel wrong or too weak/slow from silence.
- Tail from 07:51 to end still does not feel fixed.
- Overall result is not uploadable.

Important technical contradiction:
Step 23C manifest/command gates were green:
- owner_background_music_policy_enabled=true
- overall_music_gain_range_db=[-44.0,-34.0]
- owner_music_target_gain_db=-39.0
- command_contains_foreground_music_gain=false
- slow_segment_fadein_fix_enabled=true
- raw_fullmix_sidechain_blocked=true
- ffmpeg_sidechaincompress_disabled=true
- owner_tail_music_guard_passed=true
- tail_music_final_window_audible=true
- dynamic_gain_non_constant=true
- upload_started=false
- runtime_learning_started=false
- qwen_used=false

But Owner Review failed.

Goal of Step 24A:
Diagnose why the audible result still has the same music problems despite green technical gates.

Required diagnosis areas:
1. Confirm whether final MP4 audio is actually using the generated command path.
2. Inspect whether track-stage gains like +3.1 dB / 0.6 dB before automation make music feel too foreground.
3. Inspect whether final automation gains are applied after track gains as expected.
4. Compare original voice/game audio loudness vs mixed output loudness.
5. Check whether volumedetect values measured full mixed audio, not isolated music.
6. Check whether music-only stem can be rendered/extracted for diagnosis only without changing code.
7. Check whether 0.25s fades fix command text but song transitions still sound weak because source starts at quiet sections.
8. Check whether tail guard proves any music exists, but not enough perceptual audibility under game/voice.
9. Produce a clear diagnosis report with root cause candidates and one recommended fix path.

Hard locks:
- No code changes.
- No tests changes.
- No render unless explicitly diagnosis-only and approved by Master prompt.
- No upload.
- No Qwen.
- No runtime learning.
- No git add .
- No git add -A.

Expected output:
- Step 24A diagnosis report.
- GO/NO-GO for a targeted Step 24B fix.
