from pathlib import Path


def test_pipeline_imports_and_runs_render_plan_after_render_readiness_guard():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "from core.render_readiness_guard_runner import run_render_readiness_guard" in text
    assert "from core.render_plan_runner import run_render_plan_for_job" in text

    readiness_index = text.index("run_render_readiness_guard(job)")
    plan_index = text.index("run_render_plan_for_job(job)")
    assert readiness_index < plan_index

    assert '"phase": "2B-46"' in text
    assert '"render_plan_only": True' in text
    assert '"dry_run_only": True' in text
    assert '"renderer_contract_only": True' in text
    assert '"media_unchanged": True' in text
    assert '"no_execution_in_2b_46": True' in text
    assert '"no_render_in_2b_46": True' in text
    assert '"no_media_write_in_2b_46": True' in text
    assert '"no_exec_" "commands_in_2b_46": True' in text
