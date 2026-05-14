from __future__ import annotations

from typing import Any

from models.render_plan import (
    RenderOperationIntent,
    RenderPlanOutputTarget,
    RenderPlanSegment,
    RenderPlanSource,
    build_render_plan_report,
)


RENDER_PLAN_METADATA = {
    "phase": "2B-46",
    "block": "block8_render_export",
    "render_plan_only": True,
    "dry_run_only": True,
    "renderer_contract_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_46": True,
    "no_render_in_2b_46": True,
    "no_ff" "mpeg_in_2b_46": True,
    "no_media_write_in_2b_46": True,
    "no_timeline_" "apply_in_2b_46": True,
    "no_exec_commands_in_2b_46": True,
}

READY_GUARD_STATUSES = {
    "render_readiness_ready",
    "render_readiness_ready_with_warnings",
}


class RenderPlanBuilder:
    def build(self, job: Any) -> dict[str, Any]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))

        warnings: list[str] = []
        blocking_reasons: list[str] = []

        self._check_guard(job, blocking_reasons, warnings)

        timeline_items = self._timeline_items(job)
        if not timeline_items:
            blocking_reasons.append("review_timeline_items_missing")

        sources = self._build_sources(job, warnings)
        segments = self._build_segments(timeline_items, warnings, blocking_reasons)
        output_targets = self._build_output_targets(job, warnings)
        operation_intents = self._build_operation_intents(segments, output_targets)

        self._check_contract(
            sources=sources,
            segments=segments,
            output_targets=output_targets,
            operation_intents=operation_intents,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
        )

        report = build_render_plan_report(
            job_id=job_id,
            sources=sources,
            segments=segments,
            output_targets=output_targets,
            operation_intents=operation_intents,
            warnings=self._unique(warnings),
            blocking_reasons=self._unique(blocking_reasons),
            metadata=dict(RENDER_PLAN_METADATA),
        )
        return report.to_dict()

    def _check_guard(
        self,
        job: Any,
        blocking_reasons: list[str],
        warnings: list[str],
    ) -> None:
        report = self._dict(
            self._get(job, "render_readiness_guard_report")
            or self._get(job, "render_readiness_guard")
        )

        status = self._status(
            self._get(job, "render_readiness_status") or report.get("status")
        )
        job_ready_flag = self._get(job, "render_readiness_ready_for_next_render_stage")
        report_ready_flag = report.get("ready_for_next_render_stage")

        if job_ready_flag is None and report_ready_flag is None:
            ready_for_next_stage = False
        elif job_ready_flag is None:
            ready_for_next_stage = self._truthy(report_ready_flag)
        elif report_ready_flag is None:
            ready_for_next_stage = self._truthy(job_ready_flag)
        else:
            ready_for_next_stage = self._truthy(job_ready_flag) and self._truthy(report_ready_flag)

        job_start_flag = self._get(job, "render_readiness_can_start_render_pipeline")
        report_start_flag = report.get("can_start_render_pipeline")

        if job_start_flag is None and report_start_flag is None:
            can_start_pipeline = False
        elif job_start_flag is None:
            can_start_pipeline = self._truthy(report_start_flag)
        elif report_start_flag is None:
            can_start_pipeline = self._truthy(job_start_flag)
        else:
            can_start_pipeline = self._truthy(job_start_flag) and self._truthy(report_start_flag)
        blocking_count = self._int(
            self._get(job, "render_readiness_blocking_count")
            if self._get(job, "render_readiness_blocking_count") is not None
            else report.get("blocking_count", 0)
        )
        guard_blocking = self._string_list(
            self._get(job, "render_readiness_blocking_reasons")
            or report.get("blocking_reasons")
        )
        guard_warnings = self._string_list(
            self._get(job, "render_readiness_warnings")
            or report.get("warnings")
        )

        warnings.extend([f"guard_warning:{item}" for item in guard_warnings])

        if status not in READY_GUARD_STATUSES:
            blocking_reasons.append("render_plan_guard_not_ready")

        if not ready_for_next_stage:
            blocking_reasons.append("render_plan_guard_next_stage_not_ready")

        if not can_start_pipeline:
            blocking_reasons.append("render_plan_guard_cannot_start_pipeline")

        if blocking_count > 0 or guard_blocking:
            blocking_reasons.append("render_plan_guard_has_blocking_reasons")
            blocking_reasons.extend([f"guard_blocking:{item}" for item in guard_blocking])

    def _timeline_items(self, job: Any) -> list[dict[str, Any]]:
        direct = self._list(self._get(job, "review_timeline_plan_items"))
        if direct:
            return direct

        plan = self._dict(self._get(job, "review_timeline_plan"))
        report = self._dict(self._get(job, "review_timeline_plan_report"))
        dashboard = self._dict(self._get(job, "review_timeline_dashboard_package"))

        for source in (plan, report, dashboard):
            for key in (
                "items",
                "timeline_items",
                "plan_items",
                "item_cards",
                "cards",
            ):
                items = self._list(source.get(key))
                if items:
                    return items

        cards = self._list(self._get(job, "review_timeline_dashboard_item_cards"))
        if cards:
            return cards

        return []

    def _build_sources(self, job: Any, warnings: list[str]) -> list[RenderPlanSource]:
        sources: list[RenderPlanSource] = []

        path_hint = self._first_text(
            self._get(job, "input_file"),
            self._get(job, "source_file"),
            self._get(job, "media_path"),
            self._get(job, "raw_video_path"),
            self._get(job, "video_path"),
            self._get(job, "file_path"),
        )

        source_warnings: list[str] = []
        if not path_hint:
            source_warnings.append("source_path_hint_missing")
            warnings.append("render_plan_missing_source_hint")

        sources.append(
            RenderPlanSource(
                source_id="source_main",
                source_type="primary_media",
                path_hint=path_hint,
                track_id="main",
                track_type="media",
                required=True,
                available=bool(path_hint),
                warnings=source_warnings,
                metadata={
                    "path_hint_only": True,
                    "file_not_checked": True,
                    "media_not_opened": True,
                    **RENDER_PLAN_METADATA,
                },
            )
        )

        video_tracks = self._list_or_scalar_dicts(self._get(job, "video_tracks"))
        audio_tracks = self._list_or_scalar_dicts(self._get(job, "audio_tracks"))

        for index, track in enumerate(video_tracks, start=1):
            sources.append(
                RenderPlanSource(
                    source_id=f"video_track_{index}",
                    source_type="video_track",
                    path_hint=path_hint,
                    track_id=str(track.get("track_id") or track.get("id") or index),
                    track_type="video",
                    required=False,
                    available=bool(path_hint),
                    warnings=[],
                    metadata={**track, **RENDER_PLAN_METADATA},
                )
            )

        for index, track in enumerate(audio_tracks, start=1):
            sources.append(
                RenderPlanSource(
                    source_id=f"audio_track_{index}",
                    source_type="audio_track",
                    path_hint=path_hint,
                    track_id=str(track.get("track_id") or track.get("id") or index),
                    track_type="audio",
                    required=False,
                    available=bool(path_hint),
                    warnings=[],
                    metadata={**track, **RENDER_PLAN_METADATA},
                )
            )

        return sources

    def _build_segments(
        self,
        timeline_items: list[dict[str, Any]],
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> list[RenderPlanSegment]:
        segments: list[RenderPlanSegment] = []
        output_cursor = 0.0

        for index, item in enumerate(timeline_items, start=1):
            start = self._float(
                self._first_existing(
                    item,
                    "source_start_seconds",
                    "start_seconds",
                    "start",
                    "in_seconds",
                ),
                default=0.0,
            )
            end = self._float(
                self._first_existing(
                    item,
                    "source_end_seconds",
                    "end_seconds",
                    "end",
                    "out_seconds",
                ),
                default=0.0,
            )
            duration = self._float(item.get("duration_seconds"), default=end - start)
            if duration <= 0.0 and end > start:
                duration = end - start
            if end <= 0.0 and duration > 0.0:
                end = start + duration

            segment_warnings: list[str] = []
            segment_blocking: list[str] = []

            if start < 0.0 or end < 0.0:
                segment_blocking.append("negative_timing")
            if end <= start:
                segment_blocking.append("source_end_not_after_source_start")
            if duration <= 0.0:
                segment_blocking.append("duration_not_positive")

            if segment_blocking:
                blocking_reasons.append(f"render_plan_invalid_timing:item_{index}")

            output_start = round(output_cursor, 3)
            output_end = round(output_start + max(0.0, duration), 3)
            output_cursor = output_end

            transition_intent = self._intent_payload(
                item,
                keys=("transition_intent", "transition", "transition_type"),
                fallback_type="planned_transition",
            )
            censor_sfx_intent = self._censor_payload(item)
            audio_mix_intent = self._intent_payload(
                item,
                keys=("audio_mix_intent", "audio_mix", "mix_intent"),
                fallback_type="planned_audio_mix",
            )
            subtitle_intent = self._intent_payload(
                item,
                keys=("subtitle_intent", "subtitle", "subtitles"),
                fallback_type="planned_subtitle",
            )

            if censor_sfx_intent:
                warnings.append("render_plan_censor_sfx_intent_present")

            segment = RenderPlanSegment(
                segment_id=str(
                    item.get("segment_id")
                    or item.get("timeline_item_id")
                    or item.get("item_id")
                    or f"render_segment_{index}"
                ),
                source_item_id=str(
                    item.get("item_id")
                    or item.get("timeline_item_id")
                    or item.get("id")
                    or f"timeline_item_{index}"
                ),
                source_segment_id=str(
                    item.get("source_segment_id")
                    or item.get("segment_id")
                    or item.get("cut_id")
                    or f"source_segment_{index}"
                ),
                source_start_seconds=round(start, 3),
                source_end_seconds=round(end, 3),
                output_start_seconds=output_start,
                output_end_seconds=output_end,
                duration_seconds=round(max(0.0, duration), 3),
                action=str(item.get("action") or item.get("decision") or "keep"),
                transition_intent=transition_intent,
                censor_sfx_intent=censor_sfx_intent,
                audio_mix_intent=audio_mix_intent,
                subtitle_intent=subtitle_intent,
                protected=self._truthy(item.get("protected")),
                review_required=self._truthy(item.get("review_required")),
                warnings=segment_warnings,
                blocking_reasons=segment_blocking,
                metadata={
                    "source_item": dict(item),
                    "dry_run_only": True,
                    "media_unchanged": True,
                    "planned_only": True,
                },
            )
            segments.append(segment)

        return segments

    def _build_output_targets(
        self,
        job: Any,
        warnings: list[str],
    ) -> list[RenderPlanOutputTarget]:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))
        target_format = str(self._get(job, "target_format", "longform"))
        if "." in target_format:
            target_format = target_format.split(".")[-1]
        target_format = target_format.strip() or "longform"

        platform = self._platform_hint(job)

        filename_hint = f"{job_id}_render_plan_preview.mp4"
        output_path_hint = f"exports/{job_id}/{filename_hint}"

        warnings.append("output_path_is_hint_only")

        return [
            RenderPlanOutputTarget(
                target_id="output_target_main",
                target_format=target_format,
                container="mp4",
                video_codec_intent="h264",
                audio_codec_intent="aac",
                resolution_intent=str(self._get(job, "resolution_intent", "1080p60") or "1080p60"),
                fps_intent=self._float(self._get(job, "fps_intent"), default=60.0),
                audio_lufs_intent=self._float(self._get(job, "audio_lufs_intent"), default=-14.0),
                filename_hint=filename_hint,
                output_path_hint=output_path_hint,
                platform=platform,
                warnings=["hint_only_no_file_created"],
                metadata=dict(RENDER_PLAN_METADATA),
            )
        ]

    def _build_operation_intents(
        self,
        segments: list[RenderPlanSegment],
        output_targets: list[RenderPlanOutputTarget],
    ) -> list[RenderOperationIntent]:
        intents: list[RenderOperationIntent] = []

        for index, segment in enumerate(segments, start=1):
            intents.append(
                self._operation_intent(
                    index=index,
                    intent_type="trim_intent",
                    description="Later renderer should trim the source segment according to planned times.",
                    source_segment_id=segment.source_segment_id,
                    target_segment_id=segment.segment_id,
                )
            )

            if segment.transition_intent:
                intents.append(
                    self._operation_intent(
                        index=len(intents) + 1,
                        intent_type="transition_intent",
                        description="Later renderer should apply the planned transition intent.",
                        source_segment_id=segment.source_segment_id,
                        target_segment_id=segment.segment_id,
                    )
                )

            if segment.censor_sfx_intent:
                intents.append(
                    self._operation_intent(
                        index=len(intents) + 1,
                        intent_type="censor_sfx_intent",
                        description="Later renderer should apply the planned censor sound intent.",
                        source_segment_id=segment.source_segment_id,
                        target_segment_id=segment.segment_id,
                    )
                )

            if segment.audio_mix_intent:
                intents.append(
                    self._operation_intent(
                        index=len(intents) + 1,
                        intent_type="audio_mix_intent",
                        description="Later renderer should apply the planned audio mix intent.",
                        source_segment_id=segment.source_segment_id,
                        target_segment_id=segment.segment_id,
                    )
                )

            if segment.subtitle_intent:
                intents.append(
                    self._operation_intent(
                        index=len(intents) + 1,
                        intent_type="subtitle_intent",
                        description="Later renderer should apply the planned subtitle intent.",
                        source_segment_id=segment.source_segment_id,
                        target_segment_id=segment.segment_id,
                    )
                )

        if segments:
            intents.append(
                self._operation_intent(
                    index=len(intents) + 1,
                    intent_type="concat_intent",
                    description="Later renderer should join planned segments in output order.",
                )
            )

        for target in output_targets:
            intents.append(
                self._operation_intent(
                    index=len(intents) + 1,
                    intent_type="output_encode_intent",
                    description="Later renderer should encode the planned output target.",
                    target_segment_id=target.target_id,
                )
            )

        return intents

    def _operation_intent(
        self,
        *,
        index: int,
        intent_type: str,
        description: str,
        source_segment_id: str | None = None,
        target_segment_id: str | None = None,
    ) -> RenderOperationIntent:
        return RenderOperationIntent(
            intent_id=f"render_operation_intent_{index}",
            intent_type=intent_type,
            description=description,
            source_segment_id=source_segment_id,
            target_segment_id=target_segment_id,
            can_execute_now=False,
            requires_later_renderer=True,
            warnings=[],
            metadata=dict(RENDER_PLAN_METADATA),
        )

    def _check_contract(
        self,
        *,
        sources: list[RenderPlanSource],
        segments: list[RenderPlanSegment],
        output_targets: list[RenderPlanOutputTarget],
        operation_intents: list[RenderOperationIntent],
        warnings: list[str],
        blocking_reasons: list[str],
    ) -> None:
        if not segments:
            blocking_reasons.append("render_plan_no_timeline_items")

        if not output_targets:
            blocking_reasons.append("render_plan_output_target_missing")

        if not operation_intents:
            blocking_reasons.append("render_plan_operation_intents_missing")

        required_sources = [source for source in sources if source.required]
        if not required_sources:
            warnings.append("render_plan_required_source_missing")

        for source in required_sources:
            if not source.path_hint:
                warnings.append("render_plan_required_source_path_hint_missing")

        previous_end = 0.0
        for index, segment in enumerate(segments, start=1):
            if segment.output_start_seconds < previous_end:
                blocking_reasons.append(f"render_plan_output_overlap:item_{index}")
            previous_end = max(previous_end, segment.output_end_seconds)

            if segment.duration_seconds <= 0.0:
                blocking_reasons.append(f"render_plan_invalid_duration:item_{index}")

        for intent in operation_intents:
            if intent.can_execute_now:
                blocking_reasons.append("render_plan_operation_intent_executable")
            if not intent.requires_later_renderer:
                blocking_reasons.append("render_plan_operation_intent_missing_later_renderer_flag")

    def _censor_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        direct = self._dict(item.get("censor_sfx_intent"))
        if direct:
            return {**direct, "planned_only": True}

        required = self._truthy(
            item.get("censor_sfx_required")
            or item.get("censor_required")
            or item.get("profanity_censor_required")
        )
        if required:
            return {
                "intent_type": "planned_censor_sfx",
                "planned_only": True,
                "requires_later_renderer": True,
            }
        return {}

    def _intent_payload(
        self,
        item: dict[str, Any],
        *,
        keys: tuple[str, ...],
        fallback_type: str,
    ) -> dict[str, Any]:
        for key in keys:
            value = item.get(key)
            if isinstance(value, dict) and value:
                return {**value, "planned_only": True}
            if isinstance(value, str) and value.strip():
                return {
                    "intent_type": fallback_type,
                    "value": value.strip(),
                    "planned_only": True,
                    "requires_later_renderer": True,
                }
            if isinstance(value, bool) and value:
                return {
                    "intent_type": fallback_type,
                    "planned_only": True,
                    "requires_later_renderer": True,
                }
        return {}

    def _platform_hint(self, job: Any) -> str | None:
        targets = self._get(job, "target_platforms")
        if isinstance(targets, list) and targets:
            return str(targets[0])
        value = self._get(job, "platform")
        if value:
            return str(value)
        return None

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _list_or_scalar_dicts(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [dict(value)]
        return []

    def _first_existing(self, mapping: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in mapping and mapping.get(key) is not None:
                return mapping.get(key)
        return None

    def _first_text(self, *values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _status(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "1",
                "yes",
                "ready",
                "safe",
                "passed",
                "approved",
            }
        return bool(value)

    def _int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item)]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result


def build_render_plan(job: Any) -> dict[str, Any]:
    return RenderPlanBuilder().build(job)
