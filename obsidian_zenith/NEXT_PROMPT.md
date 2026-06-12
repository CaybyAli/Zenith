# PROJECT ZENITH ? CONTROLLED MUSIC PREVIEW RUN ? STEP 25B ? RENDER AFTER SMOOTH AUTOMATION + CROSSFADE FIX

Only after Master-GO.

Status:
- Phase 5: 100% / DONE
- P5-L: 100% / CLOSED
- Phase 5.5: 100% / DONE
- Step 24A/24B Audio Stem Gate Fix: DONE
- Step 25A Smooth Automation + Crossfade Fix: DONE
- Controlled Render: locked until Master-GO

Current HEAD expectation:
- f93bea8 fix(music): smooth automation and crossfadetransitions

Goal:
Create one controlled preview render after smooth gain envelope and true song crossfade fix.

Mandatory:
- Music must remain audible until the end.
- 5-second pumping must not be audible.
- max adjacent gain delta must pass.
- Song transitions must use crossfade.
- Outgoing song fades down.
- Incoming song fades up.
- No hard cut between songs.
- No transition silent gaps.
- Tail from 07:51 to end remains fixed.
- Audio-stem gates pass.
- No upload.
- No Qwen.
- No Runtime Learning.
- No Ingest.

Owner Review after render:
Ali checks:
- Does music stay smooth without 5-second loud jumps?
- Are song transitions soft?
- Does the outgoing song fade down while the next song fades in?
- Is music still background, not foreground?
- Is voice clear in front?
- Is music audible until the end?
- No audio jumps?
- Upload-worthy feeling?

Decision:
GO / FIX / NO-GO

No upload without new Master-GO.
