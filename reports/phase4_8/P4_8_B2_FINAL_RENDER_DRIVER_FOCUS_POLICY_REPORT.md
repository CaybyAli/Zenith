# PROJECT ZENITH — Phase 4.8-B2 FinalRenderDriver Focus Policy Fix

Status: B2_FIX_COMPLETE

## Scope

Changed:
- core/final_render_driver.py
- tests/test_p4_8_b2_final_render_driver_focus_policy_smoke.py

No learning corpus changes.
No A4/A5 fingerprint changes.
No timeline selection changes.

## Fix Summary

FinalRenderDriver now resolves a per-segment focus render policy from job.focus_decisions.

The resolved focus policy can override fallback ReframePlan layout decisions during render filter construction.

## New Behavior

FocusDecision focus_target mapping:

- facecam -> facecam_emphasis
- gameplay -> gameplay_crop
- balanced -> balanced_split
- drop -> gameplay_crop

## Visible Render Behavior

For 32:9 source:

- facecam_emphasis renders left half full-screen as facecam focus.
- gameplay_crop renders right half full-screen as gameplay focus.
- balanced_split keeps the existing gameplay + facecam PiP behavior.

## Render Context Evidence

FinalRenderDriver context now records:

- focus_decisions_available
- focus_decisions_used
- render_layout_counts
- resolved_render_layouts

## Tests

Proof file:
reports/phase4_8/P4_8_B2_TEST_PROOF.txt

Expected result:
8 passed

Test coverage:

1. FocusDecision gameplay overrides balanced ReframePlan layout.
2. FocusDecision facecam overrides gameplay ReframePlan layout.
3. FocusDecision balanced keeps PiP/balanced layout.
4. Render layout policy records counts for gameplay_crop, facecam_emphasis, and balanced_split.
5. Existing FinalRenderDriver filter-complex smoke tests still pass.

## Risk

Low to medium.

The change is isolated to FinalRenderDriver render policy resolution and 32:9 layout branching.

## Decision

B2_FIX_COMPLETE

Next phase:
P4.8-B3 Smooth-Zoom-Integration
