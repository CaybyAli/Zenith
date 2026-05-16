# Approval Workflow CLI

Stand: Zenith 2.C.6

## Zweck

pipeline_runner.py --approve <job_id> gibt genau einen bestehenden Job explizit frei.

Dieser Job darf das Render-Gate passieren, auch wenn eine Block-8-Stage normalerweise blocken würde.

Das ist ein pro-Job-Override. Es ersetzt nicht den globalen Auto-Approve-Mechanismus.

## Aktueller Default

Der globale Default bleibt unverändert:

ZENITH_RENDER_GATE_AUTO_APPROVE=1

Das spätere Scharfschalten auf Default 0 gehört nicht zu 2.C.6.

## Approval-Datei

Ein explizites Approval wird hier gespeichert:

exports/<channel>/<job_id>/approval.json

Beispiel:

{
  "approved": true,
  "job_id": "job_...",
  "channel": "gaming_main",
  "approved_at": "2026-05-16T00:00:00Z",
  "approved_by": "cli"
}

Es wird kein dynamisches Attribut auf dem Job-Objekt gesetzt.

## Workflow

Blockierte Jobs anzeigen:

python pipeline_runner.py --list-blocked

Einen Job freigeben und komplett neu laufen lassen:

python pipeline_runner.py --approve job_abc123

Der Runner macht dabei:

1. Job aus data/jobs.json laden
2. approval.json im Export-Ordner schreiben
3. Job für diesen Lauf wieder auf created setzen
4. Genau diesen Job erneut durch die Pipeline laufen lassen
5. Render-Gate erkennt approval.json
6. Render-Gate gibt PASS mit reason=explicitly_approved

## Kein Resume

--approve ist bewusst kein Resume-ab-Render.

Der Job läuft vollständig erneut durch die Pipeline.

Das ist robuster und vermeidet fragile Zwischenzustände.

## Render-Gate-Priorität

1. approval.json für diesen Job vorhanden -> PASS / explicitly_approved
2. Sonst normale Stage-Auswertung
3. Stage blockt + globaler Auto-Approve aktiv -> PASS / auto_approve_override
4. Stage blockt + globaler Auto-Approve aus -> BLOCKED
