# PROJECT ZENITH — Phase 4.8-B1 Render Decision Consumption Diagnosis

Status: B1_DIAGNOSIS_COMPLETE

## Current HEAD

fefc4c1 chore(P4-8-A5): audit top solo and vlog fingerprints

## Scope

No code changes.
No commit.
Diagnosis only.

## Finding Summary

The pipeline generates FocusDecision data, but the final render path does not consume it as a visible render policy.

## Evidence Chain

### 1. Focus decisions are created

File:
core/gaming_pipeline.py

Evidence:
- FocusSwitchEngine is created.
- focus_switch_engine.decide(...) is called.
- focus_decisions are summarized.
- focus_decision_log is written.
- job.focus_decisions is set.

Local evidence file:
reports/phase4_8/b1_manual/03_exact_loss_chain.txt

Relevant lines:
9355-9382

### 2. ReframePlan is built separately

File:
core/gaming_pipeline.py

Evidence:
- reframe_plan = ReframingCore().build_plan(...)
- The call passes job, timeline, highlight_candidates, aspect ratios.
- It does not pass focus_decisions.

Relevant lines:
10377-10386

### 3. Render call does not pass FocusDecision

File:
core/gaming_pipeline.py

Evidence:
- active_renderer = FinalRenderDriver()
- active_renderer.render(...) receives:
  - job
  - source_path
  - edit_timeline
  - reframe_plan
  - dynamic_edit_plan
- No focus_decisions argument is passed.

Relevant lines:
10632-10664

### 4. Guards can convert facecam_emphasis to balanced_split

Files:
core/facecam_intro_guard.py
core/facecam_zoom_smoothness_guard.py

Evidence:
- instruction.focus_kind = "balanced"
- instruction.layout_kind = "balanced_split"
- instruction.crop_window is reset to gameplay half.

Relevant lines:
facecam_intro_guard.py 120-138
facecam_zoom_smoothness_guard.py 497-515

### 5. FinalRenderDriver only has explicit 32:9 branch for facecam_emphasis

File:
core/final_render_driver.py

Evidence:
- layout_kind is read from reframe instruction.
- if layout_kind == "facecam_emphasis": render facecam-only crop.
- Otherwise it continues into Gameplay + Facecam PiP path.
- gameplay_crop and balanced_split are not clearly separated as visible render modes in this branch.

Relevant lines:
301-330

## Root Cause

FocusDecision exists, but it is not the authoritative render policy.

There are two losses:

1. Decision loss before render:
   ReframingCore builds layout decisions from FacecamGameplaySeparator/highlight metadata, not from FocusDecision.

2. Render layout loss:
   FinalRenderDriver does not explicitly consume FocusDecision and does not clearly branch gameplay_crop vs balanced_split in the 32:9 render path.

A third weakening layer exists:

3. Guard conversion:
   facecam_intro_guard and facecam_zoom_smoothness_guard can convert facecam_emphasis back to balanced_split.

## B2 Required Fix Direction

B2 should not be a blind render tweak.

Recommended B2 plan:

1. Add a small FocusDecision-to-render-policy bridge.
   The bridge should select the strongest or nearest FocusDecision for each TimelineSegment.

2. Feed the resolved decision into the render path.
   Either:
   - apply it to ReframePlan before render, or
   - pass resolved focus policy into FinalRenderDriver._build_filter_complex.

3. FinalRenderDriver must explicitly support at least:
   - facecam_focus / facecam_emphasis
   - gameplay_focus / gameplay_crop
   - balanced_split
   - drop / gameplay-only or facecam hidden

4. Render context must log:
   - focus_decisions_used
   - render_layout_counts
   - per-segment resolved focus_target
   - per-segment resolved layout_kind
   - whether layout came from FocusDecision or fallback ReframePlan

5. Tests must prove:
   - FocusDecision facecam creates visible facecam_focus/facecam_emphasis behavior.
   - FocusDecision gameplay creates gameplay_focus/gameplay_crop behavior.
   - balanced_split remains available.
   - FinalRenderDriver context records layout counts.
   - Existing non-32:9 fallback still passes.

## Risk

Medium.

The render path is central. B2 must be small and well-tested.
Do not change timeline selection.
Do not change A4/A5 fingerprints.
Do not touch learning_corpus.

## Decision

B1_DIAGNOSIS_COMPLETE

B2 is GO after this report is reviewed.
