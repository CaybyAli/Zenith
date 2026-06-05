# K3/K6 Visual Proof - DONE

Stand: 2026-06-05

Status: historischer Proof, superseded durch Phase 5 Final-GO.

## Historischer Status

- K3/K6 technisch DONE akzeptiert.
- Phase 5 Stand zum damaligen Zeitpunkt: ca. 90-92%.
- Phase 5.5: 0%, gesperrt.
- Hinweis: Die spaeteren Phase-5-Final-GO-Dokumente superseden alte Aussagen wie "K7 offen" oder "Phase 5 Final-GO: NEIN".

## Remote-Code-Stand

- HEAD: `6fef98d`
- Commit: `fix(P5-K3K6): escape libass Windows subtitle paths`

## K3 Captions - DONE

Beweise:
- Preview MP4 vorhanden.
- Preview Dauer: 4.066016s.
- Preview Aufloesung: 1080x1920.
- ASS vorhanden: `k3_caption_proof.ass`.
- Manifest vorhanden: `visual_proof_manifest.json`.
- ASS PlayResX: 1080.
- ASS PlayResY: 1920.
- Active word highlighting sichtbar.
- Owner/Friend Styles sichtbar:
  - Owner gruen: `&H0000FF00&`
  - Friend gelb: `&H0000FFFF&`
- Manifest:
  - `ass_generated_by_project_code=true`
  - `active_word_highlighting=true`
  - `owner_friend_styles=true`

Einschraenkung:
- Das Preview nutzte ein Quellvideo mit bereits eingebrannten Captions.
- Dadurch war eine doppelte Caption-Ebene sichtbar.
- Master bewertete das als Proof-Source-Artefakt, nicht als K3-Codefehler.

## K6 Layout/Fokus - DONE

Beweise:
- Preview MP4 vorhanden.
- 1080x1920 Shorts-Format.
- Layout/Reframe laut Ali sauber.
- Crop/Zoom laut Ali sauber.
- Keine kaputten schwarzen Raender.
- Layout JSON vorhanden: `k6_layout_proof.json`.
- `target_resolution=1080x1920`.
- `layout_type=hybrid_split`.
- `focus_or_reframe_codepath_used=true`.
- ffmpeg crop filter vorhanden.

## Audio

- Audio im Preview: nein.
- Grund: Preview-Tool rendert absichtlich mit `-an`.
- Bewertung: kein Blocker fuer Visual Proof.

## K7-Regel damals

Fuer K7 echten Kontroll-Run musste eine saubere Quelle ohne bereits eingebrannte Captions genutzt werden.

## Ergebnis damals

- K3: DONE.
- K6: DONE.
- K7: damals offen, inzwischen DONE.
- Phase 5 Final-GO: damals NEIN, inzwischen DONE.
- Phase 5.5: weiterhin gesperrt.
