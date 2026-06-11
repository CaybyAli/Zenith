# PROJECT ZENITH ? CONTROLLED MUSIC PREVIEW RUN ? STEP 24C ? RENDER AFTER AUDIO STEM GATE FIX

Only after Master-GO.

Status:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5: 100% / DONE
- Step 24A Deep Audio Diagnosis: DONE
- Step 24B Audio Stem Gate Fix: DONE
- EOF Cleanup: DONE
- Controlled Render: locked until Master-GO

Current HEAD expectation:
- 5763316 chore(tests): clean music output diagnostics eof
- Previous code fix:
  0b2e425 fix(music): verify preview mix with audio stem gates

Goal:
Create one controlled preview render after the audio-stem-gate fix.

Mandatory:
- Real music_auto/musicbed must cover the full video duration.
- No double music trim.
- No input -ss 30 plus atrim=start=30 double trim.
- Audio-stem gates must pass.
- music_auto tail must be audible.
- song starts must be audible.
- music-vs-voice gate must pass.
- final mix tail probe must pass.
- No upload.
- No Qwen.
- No Runtime Learning.
- No Ingest.

Owner Review after render:
Ali checks:
- Music audible until the end?
- Tail from 07:51 to end fixed?
- Song starts audible without silent ramp?
- Music is background, not foreground?
- Voice clear in front?
- No audio jumps?
- Upload-worthy feeling?

Decision:
GO / FIX / NO-GO

No upload without new Master-GO.
