# P4.8 A4 Final Re-Ingest Report

## Status

A4_FINAL_AUDIT_PASS

## Corpus Counts

- pairs: 20/20
- top_solo: 30/30
- vlogs: 3/3

## Result

A4 re-ingest completed successfully for all 20 active pair folders.

## Source Semantics

All accepted pair reports passed source semantics audit:
- transcript source: final.mp4
- hook source: final.mp4
- style capture source: final.mp4
- audio source: final.mp4
- pacing source: final.mp4
- scene/cut-density source: final.mp4
- no raw_mixed_audio as main transcript source

## Warnings

The following pairs completed with non-blocking quality warnings:

- pair_003: audio_rms_ok
- pair_006: audio_rms_ok, transcript_ok
- pair_009: transcript_ok
- pair_015: transcript_ok
- pair_020: transcript_ok

These warnings are not A4 hard failures because every accepted pair has:
- audit.ok = true
- source_semantics.ok = true
- style_fingerprint.json present
- no failed_stage

## Important Fixes Proven

- Final transcript retry windows extended.
- Final transcript offset fallback added for crashy exact-start audio.
- Final hook offset fallback added for crashy exact-start hook audio.
- pair_009 proved offset fallback works:
  - final_transcript succeeded at 5s offset 2s
  - final_hook succeeded at 5s offset 2s

## Not Started

The following phases were not started:

- A5
- B1
- B2

## Commit Readiness

Ready for git inspection and commit preparation.
