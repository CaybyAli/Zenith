from flask import Flask, render_template_string, redirect, request, url_for, jsonify
from core.job_loader import JobLoader
from core.publisher import Publisher
from core.kpi_dashboard_service import KpiDashboardService
from core.feedback_dashboard_service import FeedbackDashboardService
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from core.operations_dashboard_service import OperationsDashboardService
from core.jarvis_command_service import JarvisCommandService
from core.authorization_service import AuthorizationService
from core.access_context_service import AccessContextService
from core.jarvis_presence_service import JarvisPresenceService
from shared.role_enums import ProtectedAction
from models.publish_package import PublishPackage
from models.publish_decision import PublishDecision

from shared.channel_policies import (
    get_publish_days,
    get_publish_hour,
    get_publish_minute,
    get_upload_every_hours,
    get_retry_attempts,
    get_retry_delay_minutes,
)

from shared.enums import ChannelType
from shared.runtime_modes import RuntimeAction, RuntimeMode
import json
import os
from datetime import datetime, timedelta

from storage.local_storage_provider import LocalStorageProvider

RERENDER_JOBS_FILE = r"D:\Zenith\data\rerender_jobs.json"
JOB_STORE_FILE = r"D:\Zenith\data\jobs.json"

from jarvis.proactive_monitor import ProactiveMonitor as _ProactiveMonitor
_jarvis_monitor: _ProactiveMonitor | None = None

app = Flask(__name__)
runtime_mode_controller = RuntimeModeController()
vacation_controller = VacationController()
storage_provider = LocalStorageProvider()
kpi_dashboard_service = KpiDashboardService(storage_provider=storage_provider)
feedback_dashboard_service = FeedbackDashboardService(storage_provider=storage_provider)
operations_dashboard_service = OperationsDashboardService(storage_provider=storage_provider)
jarvis_command_service = JarvisCommandService()
authorization_service = AuthorizationService()
access_context_service = AccessContextService()
jarvis_presence_service = JarvisPresenceService()


def get_storage_provider(provider=None):
    return provider or storage_provider


def format_display_datetime(value):
    if value is None:
        return "-"

    normalized = str(value).strip()
    if not normalized:
        return "-"

    iso_candidate = normalized.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(iso_candidate)
        return parsed.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        pass

    for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            continue

    return normalized


def is_runtime_action_allowed(action):

    state = runtime_mode_controller.get_state()
    allowed = action in runtime_mode_controller.get_allowed_actions(state.mode)

    if not allowed:
        print(
            "[Dashboard] Runtime action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| mode:",
            state.mode.value,
        )

    return allowed

def is_vacation_action_allowed(action, controller=None):
    active_controller = controller or vacation_controller
    active = active_controller.is_active_now()

    blocked_actions = {
        RuntimeAction.RERENDER_QUEUE_INTAKE,
        RuntimeAction.REPOST_DISPATCH,
    }

    allowed = (not active) or (action not in blocked_actions)

    if not allowed:
        print(
            "[Dashboard] Vacation action blocked:",
            action.value if hasattr(action, "value") else str(action),
            "| effective_mode:",
            active_controller.get_effective_mode().value,
        )

    return allowed


def get_request_actor_context():
    return access_context_service.resolve_from_request(request)


def block_if_unauthorized(action: ProtectedAction):
    actor = get_request_actor_context()
    workspace_id = actor.workspace_id or "ws_main"

    if authorization_service.can_execute(
        actor,
        action,
        workspace_id=workspace_id,
    ):
        return None

    print(
        "[Dashboard] Authorization blocked:",
        f"actor={actor.actor_id}",
        f"role={actor.role.value}",
        f"workspace={workspace_id}",
        f"action={action.value}",
    )
    return redirect(url_for("index"))

HTML = """
<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="5">
    <title>Zenith Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; font-size: 14px; line-height: 1.5; }

        /* ── Layout ── */
        .layout { display: flex; min-height: 100vh; }
        .sidebar {
            width: 220px; min-width: 220px;
            background: #0d1117;
            border-right: 1px solid #21262d;
            position: fixed; top: 0; left: 0;
            height: 100vh; overflow-y: auto;
            padding: 20px 12px;
            display: flex; flex-direction: column;
        }
        .main { margin-left: 220px; flex: 1; padding: 24px; overflow-x: hidden; }

        /* ── Cards ── */
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
            margin-bottom: 16px;
        }

        /* ── Typography helpers ── */
        .section-label {
            font-size: 11px; letter-spacing: 0.08em; color: #8b949e;
            text-transform: uppercase; margin-bottom: 12px; font-weight: 500;
        }
        .card-title { font-size: 12px; color: #8b949e; font-weight: 500; margin-bottom: 10px; }
        .text-muted  { color: #8b949e; }
        .text-sm     { font-size: 12px; }
        .text-xs     { font-size: 11px; }

        /* ── KPI numbers ── */
        .kpi-number { font-size: 28px; font-weight: 700; color: #e6edf3; }
        .kpi-label  { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
        .stat-number{ font-size: 22px; font-weight: 700; color: #e6edf3; }

        /* ── Badges ── */
        .badge-done      { background: #0d2f1a; color: #3fb950; border: 1px solid #1a4a2a; border-radius: 999px; padding: 3px 10px; font-size: 12px; display: inline-block; }
        .badge-processing{ background: #2a1f00; color: #d29922; border: 1px solid #3d2e00; border-radius: 999px; padding: 3px 10px; font-size: 12px; display: inline-block; }
        .badge-failed    { background: #2d0f0f; color: #f85149; border: 1px solid #4a1a1a; border-radius: 999px; padding: 3px 10px; font-size: 12px; display: inline-block; }
        .badge-pending   { background: #1a1f2e; color: #58a6ff; border: 1px solid #2a3550; border-radius: 999px; padding: 3px 10px; font-size: 12px; display: inline-block; }
        .badge-neutral   { background: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 999px; padding: 3px 10px; font-size: 12px; display: inline-block; }

        /* ── Buttons ── */
        .btn         { padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 500; border: 1px solid; cursor: pointer; transition: all 0.15s; font-family: 'Inter', sans-serif; }
        .btn-approve { background: #0d2f1a; color: #3fb950; border-color: #1a4a2a; }
        .btn-approve:hover { background: #1a4a2a; }
        .btn-reject  { background: #2d0f0f; color: #f85149; border-color: #4a1a1a; }
        .btn-reject:hover  { background: #4a1a1a; }
        .btn-rerender{ background: #161b22; color: #58a6ff; border-color: #30363d; }
        .btn-rerender:hover{ background: #21262d; }
        .btn-publish { background: #0d2038; color: #58a6ff; border-color: #1a3a5c; }
        .btn-publish:hover { background: #1a3a5c; }

        /* ── Runtime mode buttons ── */
        .btn-mode         { padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: 'Inter', sans-serif; }
        .btn-mode-active  { border: 1px solid #3fb950; color: #3fb950; background: #0d2f1a; }
        .btn-mode-inactive{ border: 1px solid #30363d; color: #8b949e; background: #161b22; }
        .btn-mode-inactive:hover { border-color: #58a6ff; color: #58a6ff; }

        /* ── Tables ── */
        table { border-collapse: collapse; width: 100%; }
        th { font-size: 12px; color: #8b949e; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #30363d; padding: 8px 12px; text-align: left; }
        td { padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 13px; vertical-align: top; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #1c2128; }

        /* ── Sidebar nav ── */
        .nav-link { display: block; padding: 8px 12px; border-radius: 6px; color: #8b949e; text-decoration: none; font-size: 13px; margin-bottom: 2px; }
        .nav-link:hover { background: #21262d; color: #e6edf3; }

        /* ── Jarvis avatar ── */
        .jarvis-avatar {
            width: 48px; height: 48px; border-radius: 999px;
            border: 2px solid #22d3ee;
            background: radial-gradient(circle at 35% 35%, #67e8f9 0%, #22d3ee 35%, #0d1117 100%);
            animation: pulse-glow 3s ease-in-out infinite;
            flex-shrink: 0;
        }
        @keyframes pulse-glow {
            0%,100% { box-shadow: 0 0 12px rgba(34,211,238,0.3); }
            50%      { box-shadow: 0 0 24px rgba(34,211,238,0.6); }
        }
        .presence-badge { background: #161b22; border: 1px solid #30363d; border-radius: 999px; padding: 3px 8px; font-size: 11px; color: #8b949e; display: inline-block; }

        /* ── Inputs ── */
        input[type=text] {
            background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
            color: #e6edf3; padding: 8px 12px; font-family: 'Inter', sans-serif; font-size: 13px; width: 100%;
        }
        input[type=text]:focus { border-color: #58a6ff; outline: none; }

        /* ── Action group ── */
        .action-group { display: flex; flex-wrap: wrap; gap: 6px; }

        /* ── Score pills ── */
        .score-pill { background: #1a1f2e; color: #58a6ff; border: 1px solid #2a3550; border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: 600; display: inline-block; }
        .score-row  { display: flex; align-items: center; gap: 6px; margin-top: 4px; font-size: 12px; color: #8b949e; }

        /* ── Grid helpers ── */
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
        .grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }

        /* ── Misc ── */
        .section-block { margin-bottom: 24px; }
        .stat-card { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; }
        .short-item { border: 1px solid #30363d; border-radius: 6px; padding: 8px; margin-top: 6px; }
        .list-item { padding: 10px 0; }
        .list-item + .list-item { border-top: 1px solid #21262d; }
        .jarvis-response { padding: 12px; border: 1px solid #30363d; border-radius: 8px; background: #0d1117; }
    </style>
</head>
<body>
<div class="layout">

<!-- ═══════════ SIDEBAR ═══════════ -->
<aside class="sidebar">

    <div style="margin-bottom: 8px;">
        <div class="section-label">Jarvis Presence Core</div>
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
            <div class="jarvis-avatar"></div>
            <div>
                <div style="font-size:16px; font-weight:700; letter-spacing:0.04em;">{{ presence_surface["presence"]["title"] }}</div>
                <div style="font-size:11px; color:#8b949e; margin-top:2px;">{{ presence_surface["presence"]["subtitle"] }}</div>
            </div>
        </div>
        <div style="font-size:12px; color:#e6edf3; margin-bottom:10px;">{{ presence_surface["presence"]["status_line"] }}</div>
        <div style="display:flex; flex-wrap:wrap; gap:4px;">
            <span class="presence-badge">{{ presence_surface["presence"]["presence_state"] }}</span>
            <span class="presence-badge">{{ presence_surface["presence"]["alert_level"] }}</span>
            <span class="presence-badge">{{ presence_surface["presence"]["focus_label"] }}</span>
        </div>
    </div>

    <hr style="border:none; border-top:1px solid #21262d; margin:20px 0;">

    <div>
        <div class="section-label">Command Deck</div>
        <nav>
            <a class="nav-link" href="#access-context">Access</a>
            <a class="nav-link" href="#operations-overview">Overview</a>
            <a class="nav-link" href="#roles-permissions">Roles</a>
            <a class="nav-link" href="#publish-guards">Publish</a>
            <a class="nav-link" href="#system-control">Control</a>
            <a class="nav-link" href="#kpi-surface">KPI</a>
            <a class="nav-link" href="#feedback-surface">Feedback</a>
            <a class="nav-link" href="#review-grid">Review</a>
            <a class="nav-link" href="#rerender-jobs">Rerender</a>
        </nav>
    </div>

</aside>

<!-- ═══════════ MAIN ═══════════ -->
<main class="main">

<!-- ── Signal Ribbon ── -->
<div class="card">
    <div class="section-label">System Signal Ribbon</div>
    <div style="display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:14px;">
        {% for item in presence_surface["presence"]["highlight_metrics"] %}
        <div class="stat-card">
            <div class="kpi-label">{{ item["label"] }}</div>
            <div class="stat-number">{{ item["value"] }}</div>
        </div>
        {% endfor %}
    </div>
    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px;">
        <div class="stat-card">
            <div style="font-size:11px; color:#8b949e;">Workspace</div>
            <div style="font-size:13px; font-weight:600; margin-top:4px;">{{ presence_surface["presence"]["workspace_label"] }}</div>
        </div>
        <div class="stat-card">
            <div style="font-size:11px; color:#8b949e;">Actor</div>
            <div style="font-size:13px; font-weight:600; margin-top:4px;">{{ presence_surface["presence"]["actor_label"] }}</div>
        </div>
        <div class="stat-card">
            <div style="font-size:11px; color:#8b949e;">Role</div>
            <div style="font-size:13px; font-weight:600; margin-top:4px;">{{ presence_surface["presence"]["role_label"] }}</div>
        </div>
        <div class="stat-card">
            <div style="font-size:11px; color:#8b949e;">Remote</div>
            <div style="font-size:13px; font-weight:600; margin-top:4px;">
                {% if presence_surface["presence"]["is_remote"] %}true{% else %}false{% endif %}
            </div>
        </div>
    </div>
</div>

<!-- ── Access Context ── -->
<div id="access-context" class="card section-block">
    <div class="section-label">Access Context</div>
    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px;">
        <div>
            <div class="text-xs text-muted">Actor</div>
            <div style="font-size:15px; font-weight:600; margin-top:2px;">{{ actor_context["actor_id"] or "-" }}</div>
        </div>
        <div>
            <div class="text-xs text-muted">Role</div>
            <div style="font-size:15px; font-weight:600; margin-top:2px;">{{ actor_context["role"] or "-" }}</div>
        </div>
        <div>
            <div class="text-xs text-muted">Workspace</div>
            <div style="font-size:15px; font-weight:600; margin-top:2px;">{{ actor_context["workspace_id"] or "-" }}</div>
        </div>
        <div>
            <div class="text-xs text-muted">Remote</div>
            <div style="font-size:15px; font-weight:600; margin-top:2px;">
                {% if actor_context["is_remote"] %}true{% else %}false{% endif %}
            </div>
        </div>
    </div>
</div>

<!-- ── Operations Overview ── -->
<div id="operations-overview" class="section-block">
    <div class="section-label">Unified Operations Overview</div>

    <div class="grid-4">
        {% for card in operations_surface["overview"]["cards"] %}
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">{{ card["label"] }}</div>
            <div class="kpi-number">{{ card["value"] }}</div>
            <div style="font-size:12px; color:#8b949e; margin-top:6px;">{{ card["hint"] }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Top Warnings</div>
            {% if operations_surface["overview"]["top_warnings"] %}
                {% for item in operations_surface["overview"]["top_warnings"] %}
                <div class="list-item">
                    <div style="font-weight:600; margin-bottom:4px; font-size:13px;">{{ item["type"] }}</div>
                    <div style="font-size:12px; color:#8b949e;">{{ item["summary"] }}</div>
                    <div style="font-size:11px; color:#8b949e; margin-top:4px;">Severity: {{ item["severity"] }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="text-sm text-muted">Keine Warnfälle vorhanden.</div>
            {% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Top Blocked Jobs</div>
            {% if operations_surface["overview"]["top_blocked_jobs"] %}
                {% for item in operations_surface["overview"]["top_blocked_jobs"] %}
                <div class="list-item">
                    <div style="font-weight:600; margin-bottom:4px; font-size:13px;">{{ item["job_id"] }} · {{ item["title"] }}</div>
                    <div style="font-size:12px; color:#8b949e;">Channel: {{ item["channel"] }}</div>
                    <div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ item["reasons"] | join(", ") }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="text-sm text-muted">Keine blockierten Jobs vorhanden.</div>
            {% endif %}
        </div>
    </div>

    <div style="display:grid; grid-template-columns:1.2fr 0.8fr; gap:16px; margin-bottom:16px;">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Jarvis Panel</div>
            <form method="POST" action="/jarvis_command" style="display:flex; gap:8px; margin-bottom:12px;">
                <input type="text" name="jarvis_query" placeholder="{{ operations_surface['jarvis_panel']['placeholder'] }}" style="flex:1;">
                <button type="submit" class="btn btn-publish">Ask Jarvis</button>
            </form>
            <div style="font-size:12px; color:#8b949e; margin-bottom:12px;">
                {{ operations_surface["jarvis_panel"]["example_commands"] | join(" · ") }}
            </div>
            {% if jarvis_response %}
            <div class="jarvis-response">
                <div style="font-size:15px; font-weight:600; margin-bottom:6px;">{{ jarvis_response["title"] }}</div>
                <div style="font-size:13px; color:#8b949e; margin-bottom:10px;">{{ jarvis_response["summary"] }}</div>
                {% if jarvis_response["warnings"] %}
                <div style="margin-bottom:10px;">
                    <div style="font-size:12px; color:#d29922; margin-bottom:4px;">Warnings</div>
                    {% for item in jarvis_response["warnings"] %}
                    <div style="font-size:12px; color:#e6edf3; margin-top:2px;">· {{ item }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                {% if jarvis_response["details"] %}
                <div style="margin-bottom:10px;">
                    <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">Details</div>
                    {% for item in jarvis_response["details"] %}
                    <div style="font-size:12px; color:#e6edf3; margin-top:2px;">· {{ item }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                {% if jarvis_response["recommended_next_steps"] %}
                <div>
                    <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">Next Steps</div>
                    {% for item in jarvis_response["recommended_next_steps"] %}
                    <div style="font-size:12px; color:#e6edf3; margin-top:2px;">· {{ item }}</div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% else %}
            <div class="text-sm text-muted">Noch keine Jarvis-Anfrage gestellt.</div>
            {% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Top Pending Reviews</div>
            {% if operations_surface["overview"]["top_pending_reviews"] %}
                {% for item in operations_surface["overview"]["top_pending_reviews"] %}
                <div class="list-item">
                    <div style="font-weight:600; margin-bottom:4px; font-size:13px;">{{ item["job_id"] }} · {{ item["title"] }}</div>
                    <div style="font-size:12px; color:#8b949e;">Channel: {{ item["channel"] }}</div>
                    <div style="font-size:11px; color:#8b949e; margin-top:4px;">
                        Score: {{ item["final_score"] if item["final_score"] is not none else "-" }} · Shorts: {{ item["shorts_count"] }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="text-sm text-muted">Keine offenen Reviews vorhanden.</div>
            {% endif %}
        </div>
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Queue Status</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
                <div class="stat-card">
                    <div class="text-xs text-muted">Total Queue</div>
                    <div class="stat-number">{{ operations_surface["queue"]["total_entries"] }}</div>
                </div>
                <div class="stat-card">
                    <div class="text-xs text-muted">Blocked</div>
                    <div class="stat-number">{{ operations_surface["queue"]["blocked_count"] }}</div>
                </div>
            </div>
            {% if operations_surface["queue"]["state_counts"] %}
            <table>
                <tr><th>Queue State</th><th>Count</th></tr>
                {% for item in operations_surface["queue"]["state_counts"] %}
                <tr><td>{{ item["queue_state"] }}</td><td>{{ item["count"] }}</td></tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="text-sm text-muted">Noch keine Queue-Einträge vorhanden.</div>
            {% endif %}
            {% if operations_surface["queue"]["top_entries"] %}
            <div style="margin-top:12px;">
                <div class="text-xs text-muted" style="margin-bottom:6px;">Top Queue Entries</div>
                {% for item in operations_surface["queue"]["top_entries"][:5] %}
                <div style="font-size:12px; color:#e6edf3; margin-top:4px;">
                    · {{ item["topic_label"] }} | {{ item["channel_type"] }} | Score {{ item["opportunity_score"] }} | {{ item["queue_state"] }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Maintenance Status</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:12px;">
                <div class="stat-card">
                    <div class="text-xs text-muted">Integrity</div>
                    <div class="stat-number">{{ operations_surface["maintenance"]["integrity_issue_count"] }}</div>
                </div>
                <div class="stat-card">
                    <div class="text-xs text-muted">Recovery</div>
                    <div class="stat-number">{{ operations_surface["maintenance"]["recovery_action_count"] }}</div>
                </div>
                <div class="stat-card">
                    <div class="text-xs text-muted">Retention</div>
                    <div class="stat-number">{{ operations_surface["maintenance"]["retention_decision_count"] }}</div>
                </div>
            </div>
            <div class="text-sm text-muted">
                Integrity={{ operations_surface["maintenance"]["integrity_issue_count"] }},
                Recovery={{ operations_surface["maintenance"]["recovery_action_count"] }},
                Retention={{ operations_surface["maintenance"]["retention_decision_count"] }}
            </div>
        </div>
    </div>
</div>

<!-- ── Roles & Permissions ── -->
<div id="roles-permissions" class="section-block">
    <div class="section-label">Roles &amp; Permissions</div>
    <div class="card">
        <div class="card-title">Role Capability Matrix</div>
        {% if operations_surface["access_policy"]["roles"] %}
        <table>
            <tr><th>Role</th><th>Allowed Actions</th><th>Examples</th></tr>
            {% for item in operations_surface["access_policy"]["roles"] %}
            <tr>
                <td>{{ item["role"] }}</td>
                <td>{{ item["allowed_action_count"] }}</td>
                <td style="color:#8b949e;">{{ item["allowed_actions"][:5] | join(", ") }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="text-sm text-muted">Keine Rollenmatrix vorhanden.</div>
        {% endif %}
    </div>
</div>

<!-- ── Publish & Guards ── -->
<div id="publish-guards" class="section-block">
    <div class="section-label">Publish &amp; Guards</div>

    <div class="grid-5">
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Published Jobs</div>
            <div class="kpi-number">{{ operations_surface["publish"]["job_publish_stats"]["published_jobs"] }}</div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Scheduled Jobs</div>
            <div class="kpi-number">{{ operations_surface["publish"]["job_publish_stats"]["scheduled_jobs"] }}</div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Waiting Review</div>
            <div class="kpi-number">{{ operations_surface["publish"]["job_publish_stats"]["waiting_for_review_jobs"] }}</div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Retry Scheduled</div>
            <div class="kpi-number">{{ operations_surface["publish"]["job_publish_stats"]["retry_scheduled_jobs"] }}</div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Permanent Failures</div>
            <div class="kpi-number">{{ operations_surface["publish"]["job_publish_stats"]["permanently_failed_jobs"] }}</div>
        </div>
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Publish Result Status Counts</div>
            {% if operations_surface["publish"]["publish_result_counts"] %}
            <table>
                <tr><th>Status</th><th>Count</th></tr>
                {% for item in operations_surface["publish"]["publish_result_counts"] %}
                <tr><td>{{ item["publish_status"] }}</td><td>{{ item["count"] }}</td></tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="text-sm text-muted">Noch keine Publish-Resultate vorhanden.</div>
            {% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Blocked Jobs / Guard Relevance</div>
            {% if operations_surface["blocked_jobs"]["blocked_jobs"] %}
                {% for item in operations_surface["blocked_jobs"]["blocked_jobs"][:6] %}
                <div class="list-item">
                    <div style="font-weight:600; margin-bottom:4px; font-size:13px;">{{ item["job_id"] }} · {{ item["title"] }}</div>
                    <div style="font-size:12px; color:#8b949e;">Channel: {{ item["channel"] }}</div>
                    <div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ item["reasons"] | join(", ") }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="text-sm text-muted">Keine blockierten Publish-/Guard-Fälle vorhanden.</div>
            {% endif %}
        </div>
    </div>

    <div class="card">
        <div class="card-title">Recent Publish Results</div>
        {% if operations_surface["publish"]["recent_publish_results"] %}
        <table>
            <tr><th>Job</th><th>Platform</th><th>Status</th><th>Message</th></tr>
            {% for item in operations_surface["publish"]["recent_publish_results"] %}
            <tr>
                <td>{{ item["job_id"] }}</td>
                <td>{{ item["platform"] or "-" }}</td>
                <td>{{ item["publish_status"] }}</td>
                <td style="color:#8b949e;">{{ item["message"] or "-" }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="text-sm text-muted">Noch keine Recent Publish Results vorhanden.</div>
        {% endif %}
    </div>
</div>

<!-- ── System Control ── -->
<div id="system-control" class="section-block">
    <div class="section-label">System Control</div>
    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Runtime Mode</div>
            <div style="font-size:22px; font-weight:700; margin-bottom:8px;">{{ runtime_state["mode"] }}</div>
            <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">
                {% if runtime_state["mode"] == "full_power" %}Alle Worker aktiv
                {% elif runtime_state["mode"] == "balanced" %}Schonender Mischbetrieb
                {% elif runtime_state["mode"] == "stream_safe" %}Streaming sicher, Worker stark begrenzt
                {% elif runtime_state["mode"] == "gaming_safe" %}Gaming sicher, Worker stark begrenzt
                {% elif runtime_state["mode"] == "idle_only" %}Nur Idle-Arbeit erlaubt
                {% elif runtime_state["mode"] == "paused" %}Operativer Betrieb pausiert
                {% else %}-{% endif %}
            </div>
            <div style="font-size:11px; color:#8b949e; margin-bottom:16px;">Last Change: {{ runtime_state["updated_at_display"] }}</div>
            <div class="action-group">
                {% for runtime_mode in runtime_modes %}
                <form method="POST" action="/set_runtime_mode/{{ runtime_mode }}" style="display:inline;">
                    <button type="submit" class="btn-mode {% if runtime_state['mode'] == runtime_mode %}btn-mode-active{% else %}btn-mode-inactive{% endif %}">
                        {{ runtime_mode }}
                    </button>
                </form>
                {% endfor %}
            </div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Vacation Mode</div>
            <div style="font-size:22px; font-weight:700; margin-bottom:8px;">
                {% if vacation_active_now %}active_now
                {% elif vacation_state["enabled"] %}armed_waiting
                {% else %}inactive{% endif %}
            </div>
            <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">Enabled: {% if vacation_state["enabled"] %}true{% else %}false{% endif %}</div>
            <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">Start: {% if vacation_state["start_at"] %}{{ vacation_state["start_at_display"] }}{% else %}-{% endif %}</div>
            <div style="font-size:12px; color:#8b949e; margin-bottom:4px;">End: {% if vacation_state["end_at"] %}{{ vacation_state["end_at_display"] }}{% else %}-{% endif %}</div>
            <div style="font-size:11px; color:#8b949e; margin-bottom:16px;">Last Change: {{ vacation_state["updated_at_display"] }}</div>
            <div class="action-group" style="margin-bottom:12px;">
                <form method="POST" action="/set_vacation_enabled/true" style="display:inline;">
                    <button type="submit" class="btn btn-publish">Enable Vacation</button>
                </form>
                <form method="POST" action="/set_vacation_enabled/false" style="display:inline;">
                    <button type="submit" class="btn btn-reject">Disable Vacation</button>
                </form>
                <form method="POST" action="/clear_vacation_window" style="display:inline;">
                    <button type="submit" class="btn btn-rerender">Clear Window</button>
                </form>
            </div>
            <form method="POST" action="/set_vacation_window" style="display:flex; flex-wrap:wrap; gap:8px; align-items:center;">
                <input type="text" name="start_at" placeholder="TT.MM.JJJJ HH:MM" value="{{ vacation_state['start_at'] or '' }}" style="flex:1; min-width:140px;">
                <input type="text" name="end_at" placeholder="TT.MM.JJJJ HH:MM" value="{{ vacation_state['end_at'] or '' }}" style="flex:1; min-width:140px;">
                <button type="submit" class="btn btn-publish">Save Window</button>
            </form>
        </div>
    </div>
</div>

<!-- ── KPI Dashboard ── -->
<div id="kpi-surface" class="section-block">
    <div class="section-label">KPI Dashboard / Insight Surface</div>

    <div class="grid-4">
        <div class="card" style="margin-bottom:0;"><div class="kpi-label">Total KPI Entries</div><div class="kpi-number">{{ kpi_surface["total_entries"] }}</div></div>
        <div class="card" style="margin-bottom:0;"><div class="kpi-label">Winners</div><div class="kpi-number">{{ kpi_surface["winner_count"] }}</div></div>
        <div class="card" style="margin-bottom:0;"><div class="kpi-label">Losers</div><div class="kpi-number">{{ kpi_surface["loser_count"] }}</div></div>
        <div class="card" style="margin-bottom:0;"><div class="kpi-label">Outliers</div><div class="kpi-number">{{ kpi_surface["outlier_count"] }}</div></div>
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Platform Comparison</div>
            {% if kpi_surface["platform_stats"] %}
            <table>
                <tr><th>Platform</th><th>Entries</th><th>Ø Score</th><th>Top Variant</th></tr>
                {% for item in kpi_surface["platform_stats"] %}
                <tr>
                    <td>{{ item["platform"] }}</td><td>{{ item["entry_count"] }}</td>
                    <td>{{ item["average_score"] if item["average_score"] is not none else "-" }}</td>
                    <td style="color:#8b949e;">{{ item["top_variant_id"] }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch keine KPI-Daten vorhanden.</div>{% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Channel Comparison</div>
            {% if kpi_surface["channel_stats"] %}
            <table>
                <tr><th>Channel</th><th>Entries</th><th>Ø Score</th><th>Top Variant</th></tr>
                {% for item in kpi_surface["channel_stats"] %}
                <tr>
                    <td>{{ item["channel"] }}</td><td>{{ item["entry_count"] }}</td>
                    <td>{{ item["average_score"] if item["average_score"] is not none else "-" }}</td>
                    <td style="color:#8b949e;">{{ item["top_variant_id"] }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch keine KPI-Daten vorhanden.</div>{% endif %}
        </div>
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Top Performers</div>
            {% if kpi_surface["top_entries"] %}
            <table>
                <tr><th>Variant</th><th>Platform</th><th>Score</th><th>Status</th></tr>
                {% for item in kpi_surface["top_entries"] %}
                <tr>
                    <td>{{ item["variant_id"] }}</td><td>{{ item["target_platform"] }}</td>
                    <td>{{ item["performance_score"] if item["performance_score"] is not none else "-" }}</td>
                    <td>{{ item["comparison_status"] or "-" }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch keine KPI-Daten vorhanden.</div>{% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Low Performers</div>
            {% if kpi_surface["low_entries"] %}
            <table>
                <tr><th>Variant</th><th>Platform</th><th>Score</th><th>Status</th></tr>
                {% for item in kpi_surface["low_entries"] %}
                <tr>
                    <td>{{ item["variant_id"] }}</td><td>{{ item["target_platform"] }}</td>
                    <td>{{ item["performance_score"] if item["performance_score"] is not none else "-" }}</td>
                    <td>{{ item["comparison_status"] or "-" }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch keine KPI-Daten vorhanden.</div>{% endif %}
        </div>
    </div>

    <div class="card">
        <div class="card-title">Insights</div>
        {% if kpi_surface["insights"] %}
            {% for insight in kpi_surface["insights"][:6] %}
            <div class="list-item">
                <div style="font-weight:600; margin-bottom:4px; font-size:13px;">{{ insight["title"] }}</div>
                <div style="font-size:12px; color:#8b949e;">{{ insight["summary_text"] }}</div>
                <div style="font-size:11px; color:#8b949e; margin-top:4px;">Severity: {{ insight["severity"] }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="text-sm text-muted">Noch keine Insights vorhanden.</div>
        {% endif %}
    </div>
</div>

<!-- ── Feedback ── -->
<div id="feedback-surface" class="section-block">
    <div class="section-label">Feedback Learning Backbone</div>

    <div style="display:grid; grid-template-columns:180px 1fr 1fr; gap:16px; margin-bottom:16px;">
        <div class="card" style="margin-bottom:0;">
            <div class="kpi-label">Total Feedback</div>
            <div class="kpi-number">{{ feedback_surface["total_records"] }}</div>
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Feedback Categories</div>
            {% if feedback_surface["category_stats"] %}
            <table>
                <tr><th>Category</th><th>Count</th></tr>
                {% for item in feedback_surface["category_stats"] %}
                <tr><td>{{ item["category"] }}</td><td>{{ item["count"] }}</td></tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch kein Feedback vorhanden.</div>{% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Feedback Directions</div>
            {% if feedback_surface["direction_stats"] %}
            <table>
                <tr><th>Direction</th><th>Count</th></tr>
                {% for item in feedback_surface["direction_stats"] %}
                <tr><td>{{ item["direction"] }}</td><td>{{ item["count"] }}</td></tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch kein Feedback vorhanden.</div>{% endif %}
        </div>
    </div>

    <div class="grid-2">
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Recent Feedback</div>
            {% if feedback_surface["recent_feedback"] %}
            <table>
                <tr><th>Category</th><th>Direction</th><th>Variant</th><th>Text</th></tr>
                {% for item in feedback_surface["recent_feedback"][:6] %}
                <tr>
                    <td>{{ item["feedback_category"] }}</td>
                    <td>{{ item["feedback_direction"] }}</td>
                    <td style="color:#8b949e;">{{ item["variant_id"] or "-" }}</td>
                    <td style="color:#8b949e;">{{ item["feedback_text"] }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch kein Feedback vorhanden.</div>{% endif %}
        </div>
        <div class="card" style="margin-bottom:0;">
            <div class="card-title">Recurring Feedback Patterns</div>
            {% if feedback_surface["pattern_summaries"] %}
            <table>
                <tr><th>Category</th><th>Direction</th><th>Count</th></tr>
                {% for item in feedback_surface["pattern_summaries"][:6] %}
                <tr>
                    <td>{{ item["category"] }}</td>
                    <td>{{ item["direction"] }}</td>
                    <td>{{ item["item_count"] }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="text-sm text-muted">Noch keine Muster vorhanden.</div>{% endif %}
        </div>
    </div>
</div>

<!-- ── Review Grid ── -->
<div id="review-grid" class="section-block">
    <div class="section-label">Review Grid</div>
    <div class="card" style="padding:0; overflow:hidden;">
    <table>
        <tr>
            <th>Job</th>
            <th>Channel</th>
            <th>Review</th>
            <th>Publish</th>
            <th>Rerender</th>
            <th>Source</th>
            <th>Action</th>
        </tr>

        {% for job in jobs %}
        <tr>
            <td>
                <div style="font-weight:600; font-size:13px;">{{ job.job_id }}</div>
                <div style="font-size:12px; color:#8b949e; margin-top:2px;">{{ review_cards[loop.index0]["title"] }}</div>

                {% if review_cards[loop.index0]["thumbnail_path"] %}
                <div style="margin-top:8px;">
                    <img src="/thumbnail/{{ job.job_id }}" alt="Thumbnail"
                         style="max-width:140px; height:auto; border-radius:6px; border:1px solid #30363d;">
                </div>
                {% endif %}

                <div class="score-row"><span>Final</span>
                    {% if review_cards[loop.index0]["final_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["final_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>
                <div class="score-row"><span>Quality</span>
                    {% if review_cards[loop.index0]["quality_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["quality_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>
                <div class="score-row"><span>Hook</span>
                    {% if review_cards[loop.index0]["hook_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["hook_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>
                <div class="score-row"><span>Editing</span>
                    {% if review_cards[loop.index0]["editing_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["editing_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>
                <div class="score-row"><span>Retention</span>
                    {% if review_cards[loop.index0]["retention_potential_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["retention_potential_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>
                <div class="score-row"><span>Shorts</span>
                    {% if review_cards[loop.index0]["shorts_potential_score"] is not none %}<span class="score-pill">{{ review_cards[loop.index0]["shorts_potential_score"] }}</span>{% else %}<span style="color:#8b949e">-</span>{% endif %}
                </div>

                <div style="margin-top:8px; font-size:12px; color:#8b949e;">
                    Action: {% if review_cards[loop.index0]["recommended_action"] %}<span style="color:#e6edf3;">{{ review_cards[loop.index0]["recommended_action"] }}</span>{% else %}-{% endif %}
                </div>
                <div style="margin-top:4px; font-size:11px; color:#8b949e;">
                    Reason: {% if review_cards[loop.index0]["decision_reason"] %}{{ review_cards[loop.index0]["decision_reason"] }}{% else %}-{% endif %}
                </div>
                <div style="margin-top:4px; font-size:11px; color:#8b949e;">
                    Hint: {% if review_cards[loop.index0]["improvement_hint"] %}{{ review_cards[loop.index0]["improvement_hint"] }}{% else %}-{% endif %}
                </div>
                <div style="margin-top:8px; font-size:11px; color:#8b949e;">
                    Repost Status: {% if review_cards[loop.index0]["repost_status"] %}{{ review_cards[loop.index0]["repost_status"] }}{% else %}-{% endif %}
                </div>
                <div style="margin-top:2px; font-size:11px; color:#8b949e;">Repost Count: {{ review_cards[loop.index0]["repost_count"] }}</div>
                <div style="margin-top:2px; font-size:11px; color:#8b949e;">
                    Last Repost: {% if review_cards[loop.index0]["last_repost_at"] %}{{ review_cards[loop.index0]["last_repost_at"] }}{% else %}-{% endif %}
                </div>
                <div style="margin-top:6px; font-size:11px; color:#8b949e;">
                    Video: {% if review_cards[loop.index0]["video_path"] %}{{ review_cards[loop.index0]["video_path"] }}{% else %}-{% endif %}
                </div>
                <div style="margin-top:2px; font-size:11px; color:#8b949e;">
                    Shorts: {% if review_cards[loop.index0]["shorts_count"] > 0 %}{{ review_cards[loop.index0]["shorts_count"] }} Export(s){% else %}-{% endif %}
                </div>
                <div style="margin-top:2px; font-size:11px; color:#8b949e;">
                    Short Details: {% if review_cards[loop.index0]["shorts_preview"] %}{{ review_cards[loop.index0]["shorts_preview"] | join(" | ") }}{% else %}-{% endif %}
                </div>

                {% if review_cards[loop.index0]["shorts"] %}
                <div style="margin-top:8px;">
                    {% for short in review_cards[loop.index0]["shorts"] %}
                    <div class="short-item">
                        <div style="font-size:12px; color:#e6edf3;">
                            <strong>{{ short["short_id"] }}</strong>
                            &nbsp;Review:
                            {% if short["review_status"] == "approved" %}<span class="badge-done">approved</span>
                            {% elif short["review_status"] == "rejected" %}<span class="badge-failed">rejected</span>
                            {% else %}<span class="badge-pending">{{ short["review_status"] }}</span>{% endif %}
                            &nbsp;
                            {% if short["publish_status"] == "published" %}<span class="badge-done">published</span>
                            {% elif short["retry_status"] == "scheduled_retry" %}<span class="badge-processing">retry ({{ short["next_retry_at"] }})</span>
                            {% elif short["permanently_failed"] %}<span class="badge-failed">failed</span>
                            {% else %}<span class="badge-neutral">{{ short["publish_status"] }}</span>{% endif %}
                        </div>
                        <div style="font-size:11px; color:#8b949e; margin-top:4px;">
                            Segment: {% if short["segment"] %}{{ short["segment"]["label"] }} | Score: {{ short["segment"]["score"] }} | {{ short["segment"]["selection_reason"] }}{% else %}-{% endif %}
                        </div>
                        <div class="action-group" style="margin-top:6px;">
                            {% if (short["review_status"] != "approved" or short["permanently_failed"]) and short["publish_status"] != "published" %}
                            <form method="POST" action="/approve_short/{{ job.job_id }}/{{ short['short_id'] }}" style="display:inline;">
                                <button type="submit" class="btn btn-approve">Approve Short</button>
                            </form>
                            {% endif %}
                            {% if short["review_status"] != "rejected" and short["publish_status"] != "published" %}
                            <form method="POST" action="/reject_short/{{ job.job_id }}/{{ short['short_id'] }}" style="display:inline;">
                                <button type="submit" class="btn btn-reject">Reject Short</button>
                            </form>
                            {% endif %}
                            {% if short["publish_status"] == "published" %}<span class="badge-done">Short Done</span>
                            {% elif short["retry_status"] == "scheduled_retry" %}<span class="badge-processing">Retry geplant</span>
                            {% elif short["permanently_failed"] %}<span class="badge-failed">Short Failed</span>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </td>

            <td>
                <div style="font-weight:500;">{{ review_cards[loop.index0]["channel"] }}</div>
                <div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ review_cards[loop.index0]["format"] }}</div>
                <div style="font-size:11px; color:#8b949e; margin-top:4px;">
                    {% if review_cards[loop.index0]["target_platforms"] %}{{ review_cards[loop.index0]["target_platforms"] | join(", ") }}{% else %}-{% endif %}
                </div>
            </td>

            <td>
                {% if job.review_status == "pending" %}<span class="badge-pending">Pending</span>
                {% elif job.review_status == "approved" %}<span class="badge-done">Approved</span>
                {% elif job.review_status == "rejected" %}<span class="badge-failed">Rejected</span>
                {% else %}<span class="badge-neutral">{{ job.review_status or "-" }}</span>{% endif %}
            </td>

            <td>
                {% if job.publish_status == "published" %}
                <span class="badge-done">Published</span>
                {% elif job.retry_status == "scheduled_retry" %}
                <div><span class="badge-processing">Retry geplant</span></div>
                <div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ job.next_retry_at }}</div>
                {% if job.retry_count is not none and job.max_retry_attempts is not none %}
                <div style="font-size:11px; color:#8b949e;">Versuch {{ job.retry_count }} / {{ job.max_retry_attempts }}</div>
                {% endif %}
                {% elif job.permanently_failed %}
                <div><span class="badge-failed">Dauerhaft fehlgeschlagen</span></div>
                {% if job.error_message %}<div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ job.error_message }}</div>{% endif %}
                {% elif job.scheduled_at %}
                <div><span class="badge-processing">Scheduled</span></div>
                <div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ job.scheduled_at }}</div>
                {% elif job.review_status == "pending" %}
                <span class="badge-pending">Waiting for review</span>
                {% else %}
                <span style="color:#8b949e;">-</span>
                {% endif %}
            </td>

            <td>
                {% if job.is_rerender %}<span class="badge-processing">Rerender</span>
                {% else %}<span style="color:#8b949e;">-</span>{% endif %}
            </td>

            <td>
                {% if job.source_job_id %}<span class="badge-neutral">{{ job.source_job_id }}</span>
                {% else %}<span style="color:#8b949e;">-</span>{% endif %}
            </td>

            <td>
                <div class="action-group">
                    {% if job.review_status != "approved" or job.permanently_failed %}
                    <form method="POST" action="/approve/{{ job.job_id }}" style="display:inline;">
                        <button type="submit" class="btn btn-approve">Approve</button>
                    </form>
                    {% endif %}
                    {% if job.review_status != "rejected" and job.publish_status != "published" %}
                    <form method="POST" action="/reject/{{ job.job_id }}" style="display:inline;">
                        <button type="submit" class="btn btn-reject">Reject</button>
                    </form>
                    {% endif %}
                    <form method="POST" action="/rerender/{{ job.job_id }}" style="display:inline;">
                        <button type="submit" class="btn btn-rerender">Rerender</button>
                    </form>

                    {% if job.publish_status == "published" %}
                        {% if review_cards[loop.index0]["repost_requested"] %}
                        <span class="badge-processing">Repost Requested</span>
                        {% else %}
                        <form method="POST" action="/repost/{{ job.job_id }}" style="display:inline;">
                            <button type="submit" class="btn btn-publish">Repost Video</button>
                        </form>
                        {% endif %}
                        <span class="badge-done">Video Done</span>
                    {% elif job.review_status == "approved" and not job.permanently_failed %}
                    <form method="POST" action="/publish/{{ job.job_id }}" style="display:inline;">
                        <button type="submit" class="btn btn-publish">Publish Video</button>
                    </form>
                    {% endif %}

                    {% set short_flags = namespace(has_publishable_short=false, all_shorts_published=true) %}
                    {% for short in review_cards[loop.index0]["shorts"] %}
                        {% if short["review_status"] == "approved" and short["publish_status"] != "published" and not short["permanently_failed"] %}
                            {% set short_flags.has_publishable_short = true %}
                        {% endif %}
                        {% if short["publish_status"] != "published" %}
                            {% set short_flags.all_shorts_published = false %}
                        {% endif %}
                    {% endfor %}

                    {% if short_flags.has_publishable_short %}
                    <form method="POST" action="/publish_shorts/{{ job.job_id }}" style="display:inline;">
                        <button type="submit" class="btn btn-publish">Publish Shorts</button>
                    </form>
                    {% elif review_cards[loop.index0]["shorts_count"] > 0 and short_flags.all_shorts_published %}
                    <span class="badge-done">Shorts Done</span>
                    {% endif %}
                </div>
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>
</div>

<!-- ── Rerender Jobs ── -->
<div id="rerender-jobs" class="section-block">
    <div class="section-label">Rerender Jobs</div>
    <div class="card" style="padding:0; overflow:hidden;">
    <table>
        <tr>
            <th>ID</th>
            <th>Source</th>
            <th>Channel</th>
            <th>Status</th>
        </tr>
        {% for job in rerender_jobs %}
        <tr>
            <td>{{ job.rerender_job_id }}</td>
            <td>{{ job.source_job_id }}</td>
            <td>
                {% if job.channel_type == "gaming_main" %}Main
                {% elif job.channel_type == "gaming_uncut" or job.channel_type == "uncut" %}Uncut
                {% elif job.channel_type == "faceless_trend" %}Faceless Trend
                {% else %}{{ job.channel_type }}{% endif %}
            </td>
            <td>
                {% if job.status == "pending" %}<span class="badge-pending">Pending</span>
                {% elif job.status == "processing" %}<span class="badge-processing">Processing</span>
                {% elif job.status == "done" %}<span class="badge-done">Done</span>
                {% elif job.status == "failed_missing_source" %}
                <div><span class="badge-failed">Failed: Missing Source</span></div>
                {% if job.error_reason %}<div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ job.error_reason }}</div>{% endif %}
                {% elif job.status == "failed_runtime" %}
                <div><span class="badge-failed">Failed: Runtime Error</span></div>
                {% if job.error_reason %}<div style="font-size:11px; color:#8b949e; margin-top:4px;">{{ job.error_reason }}</div>{% endif %}
                {% else %}<span class="badge-neutral">{{ job.status }}</span>{% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>
</div>

</main>
</div><!-- /.layout -->

<div id="jarvis-toast-container" style="position:fixed;top:20px;right:20px;z-index:9999;max-width:380px;pointer-events:none;"></div>
<style>
.jarvis-toast{
  background:linear-gradient(135deg,#0d1b2a 0%,#1a2a3a 100%);
  border:1px solid #00d4ff;
  border-radius:8px;
  color:#e0f7fa;
  padding:14px 18px;
  margin-bottom:10px;
  box-shadow:0 4px 20px rgba(0,212,255,0.3);
  font-family:monospace;
  font-size:13px;
  line-height:1.45;
  opacity:0;
  transform:translateX(110%);
  transition:opacity .3s ease,transform .3s ease;
  pointer-events:auto;
  cursor:pointer;
}
.jarvis-toast.jarvis-show{opacity:1;transform:translateX(0);}
.jarvis-toast-label{
  color:#00d4ff;font-weight:bold;font-size:10px;
  text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;
}
</style>
<script>
(function(){
  var _container=document.getElementById('jarvis-toast-container');
  function _showToast(alert){
    var div=document.createElement('div');
    div.className='jarvis-toast';
    div.innerHTML='<div class="jarvis-toast-label">&#9670; JARVIS</div>'+
      _esc(alert.message||'');
    _container.appendChild(div);
    setTimeout(function(){div.classList.add('jarvis-show');},20);
    function _dismiss(){
      div.classList.remove('jarvis-show');
      setTimeout(function(){if(div.parentNode)div.remove();},350);
    }
    div.onclick=_dismiss;
    setTimeout(_dismiss,12000);
  }
  function _esc(s){
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  function _poll(){
    fetch('/api/jarvis/alerts')
      .then(function(r){return r.json();})
      .then(function(d){(d.alerts||[]).forEach(_showToast);})
      .catch(function(){});
  }
  setTimeout(_poll,5000);
  setInterval(_poll,60000);
})();
</script>

</body>
</html>
"""


@app.route("/")
def index():
    from shared.job_review_view import build_review_card_data

    loader = JobLoader()
    jobs = list(loader.load_all_jobs(base_path="exports"))

    review_cards = [build_review_card_data(job) for job in jobs]
    rerender_jobs = load_rerender_jobs()

    actor_context = access_context_service.resolve_actor_context()

    runtime_state = runtime_mode_controller.get_state().to_dict()
    runtime_state["updated_at_display"] = format_display_datetime(runtime_state.get("updated_at"))
    runtime_modes = [mode.value for mode in RuntimeMode]

    vacation_state = vacation_controller.get_state().to_dict()
    vacation_state["start_at_display"] = format_display_datetime(vacation_state.get("start_at"))
    vacation_state["end_at_display"] = format_display_datetime(vacation_state.get("end_at"))
    vacation_state["updated_at_display"] = format_display_datetime(vacation_state.get("updated_at"))
    vacation_active_now = vacation_controller.is_active_now()
    kpi_surface = kpi_dashboard_service.build_surface(base_path="exports")
    feedback_surface = feedback_dashboard_service.build_surface(base_path="exports")
    operations_surface = operations_dashboard_service.build_operations_surface(
        base_path="exports",
        rerender_queue_file=r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file=r"D:\Zenith\data\rerender_jobs.json",
    )
    presence_surface = jarvis_presence_service.build_presence_surface(
        base_path="exports",
        rerender_queue_file=r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file=r"D:\Zenith\data\rerender_jobs.json",
    )
    jarvis_response = None

    return render_template_string(
        HTML,
        jobs=jobs,
        review_cards=review_cards,
        rerender_jobs=rerender_jobs,
        runtime_state=runtime_state,
        runtime_modes=runtime_modes,
        vacation_state=vacation_state,
        vacation_active_now=vacation_active_now,
        kpi_surface=kpi_surface,
        feedback_surface=feedback_surface,
        operations_surface=operations_surface,
        presence_surface=presence_surface,
        jarvis_response=jarvis_response,
        actor_context=actor_context.to_dict(),
    )

@app.route("/jarvis_command", methods=["POST"])
def jarvis_command():
    auth_block = block_if_unauthorized(ProtectedAction.USE_JARVIS)
    if auth_block is not None:
        return auth_block

    from shared.job_review_view import build_review_card_data

    query = (request.form.get("jarvis_query") or "").strip()
    actor_context = get_request_actor_context()

    loader = JobLoader()
    jobs = list(loader.load_all_jobs(base_path="exports"))
    review_cards = [build_review_card_data(job) for job in jobs]
    rerender_jobs = load_rerender_jobs()

    runtime_state = runtime_mode_controller.get_state().to_dict()
    runtime_state["updated_at_display"] = format_display_datetime(runtime_state.get("updated_at"))
    runtime_modes = [mode.value for mode in RuntimeMode]

    vacation_state = vacation_controller.get_state().to_dict()
    vacation_state["start_at_display"] = format_display_datetime(vacation_state.get("start_at"))
    vacation_state["end_at_display"] = format_display_datetime(vacation_state.get("end_at"))
    vacation_state["updated_at_display"] = format_display_datetime(vacation_state.get("updated_at"))
    vacation_active_now = vacation_controller.is_active_now()

    kpi_surface = kpi_dashboard_service.build_surface(base_path="exports")
    feedback_surface = feedback_dashboard_service.build_surface(base_path="exports")
    operations_surface = operations_dashboard_service.build_operations_surface(
        base_path="exports",
        rerender_queue_file=r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file=r"D:\Zenith\data\rerender_jobs.json",
    )
    presence_surface = jarvis_presence_service.build_presence_surface(
        base_path="exports",
        rerender_queue_file=r"D:\Zenith\data\rerender_queue.json",
        rerender_jobs_file=r"D:\Zenith\data\rerender_jobs.json",
    )

    if query:
        jarvis_response = jarvis_command_service.handle_command(
            query,
            base_path="exports",
            rerender_queue_file=r"D:\Zenith\data\rerender_queue.json",
            rerender_jobs_file=r"D:\Zenith\data\rerender_jobs.json",
        ).to_dict()
    else:
        jarvis_response = {
            "title": "Jarvis",
            "summary": "Keine Anfrage übergeben.",
            "details": [],
            "warnings": [],
            "recommended_next_steps": [],
            "evidence_sections": [],
        }

    return render_template_string(
        HTML,
        jobs=jobs,
        review_cards=review_cards,
        rerender_jobs=rerender_jobs,
        runtime_state=runtime_state,
        runtime_modes=runtime_modes,
        vacation_state=vacation_state,
        vacation_active_now=vacation_active_now,
        kpi_surface=kpi_surface,
        feedback_surface=feedback_surface,
        operations_surface=operations_surface,
        presence_surface=presence_surface,
        jarvis_response=jarvis_response,
        actor_context=actor_context.to_dict(),
    )

@app.route("/set_vacation_enabled/<enabled_value>", methods=["POST"])
def set_vacation_enabled(enabled_value):
    auth_block = block_if_unauthorized(ProtectedAction.SET_VACATION_STATE)
    if auth_block is not None:
        return auth_block

    normalized = str(enabled_value).strip().lower()
    enabled = normalized == "true"
    vacation_controller.set_enabled(enabled)
    print(f"[Dashboard] Vacation enabled changed to: {enabled}")
    return redirect(url_for("index"))


@app.route("/set_vacation_window", methods=["POST"])
def set_vacation_window():
    auth_block = block_if_unauthorized(ProtectedAction.SET_VACATION_STATE)
    if auth_block is not None:
        return auth_block

    start_at = request.form.get("start_at")
    end_at = request.form.get("end_at")

    try:
        vacation_controller.set_window(start_at, end_at)
        print(f"[Dashboard] Vacation window saved: start_at={start_at}, end_at={end_at}")
    except Exception as e:
        print(f"[Dashboard] Vacation window save failed: {e}")

    return redirect(url_for("index"))

@app.route("/set_runtime_mode/<mode_value>", methods=["GET", "POST"])
def set_runtime_mode(mode_value):
    auth_block = block_if_unauthorized(ProtectedAction.SET_RUNTIME_MODE)
    if auth_block is not None:
        return auth_block

    runtime_mode_controller.set_mode(mode_value)
    print(f"[Dashboard] Runtime mode changed to: {mode_value}")
    return redirect(url_for("index"))


@app.route("/clear_vacation_window", methods=["POST"])
def clear_vacation_window():
    auth_block = block_if_unauthorized(ProtectedAction.SET_VACATION_STATE)
    if auth_block is not None:
        return auth_block

    vacation_controller.clear_window()
    print("[Dashboard] Vacation window cleared")
    return redirect(url_for("index"))

@app.route("/approve/<job_id>", methods=["POST"])
def approve(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.REVIEW_DECISION)
    if auth_block is not None:
        return auth_block

    update_job_status(job_id, "approved")
    return redirect(url_for("index"))


@app.route("/reject/<job_id>", methods=["POST"])
def reject(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.REVIEW_DECISION)
    if auth_block is not None:
        return auth_block

    update_job_status(job_id, "rejected")
    return redirect(url_for("index"))

@app.route("/approve_short/<job_id>/<short_id>", methods=["POST"])
def approve_short(job_id, short_id):
    auth_block = block_if_unauthorized(ProtectedAction.SHORT_REVIEW_DECISION)
    if auth_block is not None:
        return auth_block

    update_single_short_review_status(job_id, short_id, "approved")
    return redirect(url_for("index"))


@app.route("/reject_short/<job_id>/<short_id>", methods=["POST"])
def reject_short(job_id, short_id):
    auth_block = block_if_unauthorized(ProtectedAction.SHORT_REVIEW_DECISION)
    if auth_block is not None:
        return auth_block

    update_single_short_review_status(job_id, short_id, "rejected")
    return redirect(url_for("index"))

@app.route("/rerender/<job_id>", methods=["POST"])
def rerender(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.RERENDER)
    if auth_block is not None:
        return auth_block

    if not is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
        print(f"[Dashboard] Rerender blocked by runtime mode for {job_id}")
        return redirect(url_for("index"))

    if not is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE):
        print(f"[Dashboard] Rerender blocked by vacation mode for {job_id}")
        return redirect(url_for("index"))

    trigger_rerender(job_id)
    return redirect(url_for("index"))

@app.route("/repost/<job_id>", methods=["POST"])
def repost(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.REPOST)
    if auth_block is not None:
        return auth_block

    if not is_runtime_action_allowed(RuntimeAction.REPOST_DISPATCH):
        print(f"[Dashboard] Repost blocked by runtime mode for {job_id}")
        return redirect(url_for("index"))

    if not is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH):
        print(f"[Dashboard] Repost blocked by vacation mode for {job_id}")
        return redirect(url_for("index"))

    trigger_repost(job_id)
    return redirect(url_for("index"))


@app.route("/publish/<job_id>", methods=["POST"])
def publish(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.PUBLISH_VIDEO)
    if auth_block is not None:
        return auth_block

    if not is_runtime_action_allowed(RuntimeAction.PUBLISH_DISPATCH):
        print(f"[Dashboard] Publish blocked by runtime mode for {job_id}")
        return redirect(url_for("index"))

    data = load_publish_package(job_id)

    if not data:
        print("Job nicht gefunden:", job_id)
        return redirect(url_for("index"))

    try:
        publish_package = PublishPackage(
            job_id=data["job_id"],
            video_path=data["video_path"],
            title=data["title"],
            description=data["description"],
            hashtags=data.get("hashtags", []),
            thumbnail_path=data.get("thumbnail_path"),
            platform_targets=data.get("platform_targets", []),
            channel_type=ChannelType(data["channel_type"]),
        )

        publish_decision = PublishDecision(
            job_id=data["job_id"],
            decision="autopublish_allowed",
            reason="Manual publish from dashboard",
        )

        publisher = Publisher()
        publish_result = publisher.publish(publish_package, publish_decision)

        print(f"[Dashboard] Published main video: {job_id}")
        print(publish_result)

        mark_job_as_published(job_id)

    except Exception as e:
        print(f"[Dashboard] Publish Fehler bei {job_id}: {e}")

    return redirect(url_for("index"))


@app.route("/publish_shorts/<job_id>", methods=["POST"])
def publish_shorts(job_id):
    auth_block = block_if_unauthorized(ProtectedAction.PUBLISH_SHORTS)
    if auth_block is not None:
        return auth_block

    if not is_runtime_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH):
        print(f"[Dashboard] Shorts publish blocked by runtime mode for {job_id}")
        return redirect(url_for("index"))

    data = load_publish_package(job_id)

    if not data:
        print("Job nicht gefunden:", job_id)
        return redirect(url_for("index"))

    published_short_ids = []

    try:
        publisher = Publisher()

        for index, short in enumerate(data.get("shorts", []), start=1):
            short_id = (
                short.get("short_id")
                if isinstance(short, dict) and short.get("short_id")
                else f"short_{index}"
            )

            short_path = (
                short.get("path")
                if isinstance(short, dict)
                else short
            )

            short_review_status = (
                short.get("review_status")
                if isinstance(short, dict) and short.get("review_status")
                else "pending"
            )

            short_publish_status = (
                short.get("publish_status")
                if isinstance(short, dict) and short.get("publish_status")
                else "not_published"
            )

            short_permanently_failed = (
                bool(short.get("permanently_failed", False))
                if isinstance(short, dict)
                else False
            )

            short_platform_targets = (
                list(short.get("platform_targets"))
                if isinstance(short, dict) and short.get("platform_targets")
                else list(data.get("platform_targets") or data.get("target_platforms") or [])
            )

            if not short_path:
                continue

            if short_review_status != "approved":
                continue

            if short_publish_status == "published":
                continue

            if short_permanently_failed:
                continue

            publish_package = PublishPackage(
                job_id=data["job_id"],
                video_path=short_path,
                title=f'{data["title"]} [{short_id}]',
                description=data["description"],
                hashtags=data.get("hashtags", []),
                thumbnail_path=data.get("thumbnail_path"),
                platform_targets=short_platform_targets,
                channel_type=ChannelType(data["channel_type"]),
                short_id=short_id,
            )

            publish_decision = PublishDecision(
                job_id=data["job_id"],
                decision="autopublish_allowed",
                reason=f"Manual short publish from dashboard: {short_id}",
            )

            try:
                publish_result = publisher.publish(publish_package, publish_decision)
                print(f"[Dashboard] Published short: {job_id} / {short_id}")
                print(publish_result)

                published_short_ids.append(short_id)

            except Exception as e:
                print(f"[Dashboard] Short Publish Fehler bei {job_id} / {short_id}: {e}")
                schedule_short_retry_or_fail(job_id, short_id, str(e))

        if published_short_ids:
            mark_selected_shorts_as_published(job_id, published_short_ids)
        else:
            print(f"[Dashboard] Keine publishbaren Shorts gefunden für {job_id}")

    except Exception as e:
        print(f"[Dashboard] Shorts Publish Fehler bei {job_id}: {e}")

    return redirect(url_for("index"))


@app.route("/thumbnail/<job_id>")
def thumbnail(job_id):
    storage = get_storage_provider()
    data = load_publish_package(job_id, provider=storage)

    if not data:
        return "", 404

    thumbnail_path = data.get("thumbnail_path")

    if not thumbnail_path:
        return "", 404

    if not storage.exists(thumbnail_path):
        return "", 404

    from flask import send_file
    return send_file(thumbnail_path)


def update_job_status(job_id, new_status, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)
            data["review_status"] = new_status

            if new_status == "approved":
                data["error_message"] = None
                data["retry_count"] = 0
                data["next_retry_at"] = None
                data["last_retry_at"] = None
                data["last_retry_reason"] = None
                data["retry_status"] = None
                data["permanently_failed"] = False
                data["publish_status"] = None

                now = datetime.now()

                publish_days = get_publish_days(data["channel_type"])
                publish_hour = get_publish_hour(data["channel_type"])
                publish_minute = get_publish_minute(data["channel_type"])

                if publish_days:
                    scheduled_dt = None

                    for day_offset in range(8):
                        candidate_day = now + timedelta(days=day_offset)
                        candidate_dt = candidate_day.replace(
                            hour=publish_hour,
                            minute=publish_minute,
                            second=0,
                            microsecond=0,
                        )

                        if candidate_day.weekday() in publish_days and candidate_dt > now:
                            scheduled_dt = candidate_dt
                            break

                    if scheduled_dt is not None:
                        data["is_scheduled"] = True
                        data["scheduled_at"] = scheduled_dt.strftime("%Y-%m-%d %H:%M")
                    else:
                        data["is_scheduled"] = False
                        data["scheduled_at"] = None

                elif get_upload_every_hours(data["channel_type"]):
                    scheduled_dt = now + timedelta(
                        hours=get_upload_every_hours(data["channel_type"])
                    )
                    data["is_scheduled"] = True
                    data["scheduled_at"] = scheduled_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    data["is_scheduled"] = False
                    data["scheduled_at"] = None

            if new_status == "rejected":
                data["is_scheduled"] = False
                data["scheduled_at"] = None

            storage.write_json(job_file, data, indent=4)

            update_job_store_fields(job_id, {
                "review_status": data.get("review_status"),
                "scheduled_at": data.get("scheduled_at"),
                "is_scheduled": data.get("is_scheduled"),
                "error_message": data.get("error_message"),
                "retry_count": data.get("retry_count"),
                "next_retry_at": data.get("next_retry_at"),
                "last_retry_at": data.get("last_retry_at"),
                "last_retry_reason": data.get("last_retry_reason"),
                "retry_status": data.get("retry_status"),
                "permanently_failed": data.get("permanently_failed"),
                "publish_status": data.get("publish_status"),
            }, provider=storage)

            print("Updated main job:", job_id, "->", new_status)
            return

def update_single_short_review_status(job_id, short_id, new_status, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)

            normalized_shorts = []
            for index, short in enumerate(data.get("shorts", []), start=1):
                current_short_id = (
                    short.get("short_id")
                    if isinstance(short, dict) and short.get("short_id")
                    else f"short_{index}"
                )

                short_data = {
                    "short_id": current_short_id,
                    "path": (
                        short.get("path")
                        if isinstance(short, dict)
                        else short
                    ),
                    "status": (
                        short.get("status")
                        if isinstance(short, dict) and short.get("status")
                        else "generated"
                    ),
                    "review_status": (
                        new_status
                        if current_short_id == short_id
                        else (
                            short.get("review_status")
                            if isinstance(short, dict) and short.get("review_status")
                            else "pending"
                        )
                    ),
                    "platform_targets": (
                        list(short.get("platform_targets"))
                        if isinstance(short, dict) and short.get("platform_targets")
                        else list(data.get("platform_targets") or data.get("target_platforms") or [])
                    ),
                    "publish_status": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            short.get("publish_status")
                            if isinstance(short, dict) and short.get("publish_status") is not None
                            else "not_published"
                        )
                    ),
                    "retry_count": (
                        0
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            int(short.get("retry_count", 0))
                            if isinstance(short, dict)
                            else 0
                        )
                    ),
                    "max_retry_attempts": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            int(short["max_retry_attempts"])
                            if isinstance(short, dict) and short.get("max_retry_attempts") is not None
                            else None
                        )
                    ),
                    "retry_delay_minutes": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            int(short["retry_delay_minutes"])
                            if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
                            else None
                        )
                    ),
                    "next_retry_at": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            short.get("next_retry_at")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "last_retry_at": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            short.get("last_retry_at")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "last_retry_reason": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            short.get("last_retry_reason")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "retry_status": (
                        None
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            short.get("retry_status")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "permanently_failed": (
                        False
                        if current_short_id == short_id and new_status == "approved"
                        else (
                            bool(short.get("permanently_failed", False))
                            if isinstance(short, dict)
                            else False
                        )
                    ),
                    "segment": (
                        {
                            "label": short["segment"].get("label"),
                            "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                            "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                            "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                            "score": float(short["segment"].get("score", 0.0)),
                            "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
                        }
                        if isinstance(short, dict) and isinstance(short.get("segment"), dict)
                        else None
                    ),
                }

                if short_data["path"]:
                    normalized_shorts.append(short_data)

            data["shorts"] = normalized_shorts
            storage.write_json(job_file, data, indent=4)

            print(f"Updated short: {job_id} / {short_id} -> {new_status}")
            return

def trigger_rerender(job_id, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)
            data["rerender_requested"] = True
            storage.write_json(job_file, data, indent=4)

            print(f"[Dashboard] Rerender requested for {job_id}")
            return

def trigger_repost(job_id, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)
            data["repost_requested"] = True
            data["repost_status"] = "requested"
            storage.write_json(job_file, data, indent=4)

            print(f"[Dashboard] Repost requested for {job_id}")
            return

def load_rerender_jobs(provider=None):
    storage = get_storage_provider(provider)

    if not storage.exists(RERENDER_JOBS_FILE):
        return []

    try:
        data = storage.read_json(RERENDER_JOBS_FILE)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_publish_package(job_id, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return None

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if storage.exists(job_file):
                return storage.read_json(job_file)

    return None

def update_job_store_fields(job_id, updates, provider=None):
    storage = get_storage_provider(provider)

    if not storage.exists(JOB_STORE_FILE):
        return

    try:
        data = storage.read_json(JOB_STORE_FILE)

        jobs = data.get("jobs", {})
        if job_id not in jobs:
            return

        jobs[job_id].update(updates)
        storage.write_json(JOB_STORE_FILE, data, indent=4)

        print(f"[Dashboard] JobStore synchronisiert für {job_id}")

    except Exception as e:
        print(f"[Dashboard] JobStore Sync Fehler bei {job_id}: {e}")

def mark_job_as_published(job_id, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)

            data["publish_status"] = "published"
            data["error_message"] = None
            data["retry_count"] = 0
            data["next_retry_at"] = None
            data["last_retry_at"] = datetime.now().isoformat()
            data["last_retry_reason"] = None
            data["retry_status"] = None
            data["permanently_failed"] = False
            data["is_scheduled"] = False
            data["scheduled_at"] = None

            storage.write_json(job_file, data, indent=4)

            update_job_store_fields(job_id, {
                "publish_status": data.get("publish_status"),
                "error_message": data.get("error_message"),
                "retry_count": data.get("retry_count"),
                "next_retry_at": data.get("next_retry_at"),
                "last_retry_at": data.get("last_retry_at"),
                "last_retry_reason": data.get("last_retry_reason"),
                "retry_status": data.get("retry_status"),
                "permanently_failed": data.get("permanently_failed"),
                "is_scheduled": data.get("is_scheduled"),
                "scheduled_at": data.get("scheduled_at"),
            }, provider=storage)

            print(f"[Dashboard] publish_status gesetzt für Hauptvideo {job_id}")
            return


def mark_selected_shorts_as_published(job_id, published_short_ids, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)

            normalized_shorts = []
            for index, short in enumerate(data.get("shorts", []), start=1):
                short_id = (
                    short.get("short_id")
                    if isinstance(short, dict) and short.get("short_id")
                    else f"short_{index}"
                )

                short_data = {
                    "short_id": short_id,
                    "path": (
                        short.get("path")
                        if isinstance(short, dict)
                        else short
                    ),
                    "status": (
                        short.get("status")
                        if isinstance(short, dict) and short.get("status")
                        else "generated"
                    ),
                    "review_status": (
                        short.get("review_status")
                        if isinstance(short, dict) and short.get("review_status")
                        else "pending"
                    ),
                    "platform_targets": (
                        list(short.get("platform_targets"))
                        if isinstance(short, dict) and short.get("platform_targets")
                        else list(data.get("platform_targets") or data.get("target_platforms") or [])
                    ),
                    "publish_status": (
                        "published"
                        if short_id in published_short_ids
                        else (
                            short.get("publish_status")
                            if isinstance(short, dict) and short.get("publish_status") is not None
                            else "not_published"
                        )
                    ),
                    "retry_count": (
                        0
                        if short_id in published_short_ids
                        else (
                            int(short.get("retry_count", 0))
                            if isinstance(short, dict)
                            else 0
                        )
                    ),
                    "max_retry_attempts": (
                        None
                        if short_id in published_short_ids
                        else (
                            int(short["max_retry_attempts"])
                            if isinstance(short, dict) and short.get("max_retry_attempts") is not None
                            else None
                        )
                    ),
                    "retry_delay_minutes": (
                        None
                        if short_id in published_short_ids
                        else (
                            int(short["retry_delay_minutes"])
                            if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
                            else None
                        )
                    ),
                    "next_retry_at": (
                        None
                        if short_id in published_short_ids
                        else (
                            short.get("next_retry_at")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "last_retry_at": (
                        datetime.now().isoformat()
                        if short_id in published_short_ids
                        else (
                            short.get("last_retry_at")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "last_retry_reason": (
                        None
                        if short_id in published_short_ids
                        else (
                            short.get("last_retry_reason")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "retry_status": (
                        None
                        if short_id in published_short_ids
                        else (
                            short.get("retry_status")
                            if isinstance(short, dict)
                            else None
                        )
                    ),
                    "permanently_failed": (
                        False
                        if short_id in published_short_ids
                        else (
                            bool(short.get("permanently_failed", False))
                            if isinstance(short, dict)
                            else False
                        )
                    ),
                    "segment": (
                        {
                            "label": short["segment"].get("label"),
                            "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                            "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                            "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                            "score": float(short["segment"].get("score", 0.0)),
                            "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
                        }
                        if isinstance(short, dict) and isinstance(short.get("segment"), dict)
                        else None
                    ),
                }

                if short_data["path"]:
                    normalized_shorts.append(short_data)

            data["shorts"] = normalized_shorts
            storage.write_json(job_file, data, indent=4)

            print(f"[Dashboard] Shorts publish_status gesetzt für {job_id}: {published_short_ids}")
            return

def schedule_short_retry_or_fail(job_id, short_id, error_message, provider=None):
    storage = get_storage_provider(provider)
    base_path = "exports"

    if not storage.exists(base_path):
        return

    for channel in storage.list_dir(base_path):
        channel_path = storage.join(base_path, channel)

        if not storage.is_dir(channel_path):
            continue

        for job_folder in storage.list_dir(channel_path):
            if job_folder != job_id:
                continue

            job_file = storage.join(channel_path, job_folder, "job.json")

            if not storage.exists(job_file):
                continue

            data = storage.read_json(job_file)

            normalized_shorts = []
            for index, short in enumerate(data.get("shorts", []), start=1):
                current_short_id = (
                    short.get("short_id")
                    if isinstance(short, dict) and short.get("short_id")
                    else f"short_{index}"
                )

                short_data = {
                    "short_id": current_short_id,
                    "path": (
                        short.get("path")
                        if isinstance(short, dict)
                        else short
                    ),
                    "status": (
                        short.get("status")
                        if isinstance(short, dict) and short.get("status")
                        else "generated"
                    ),
                    "review_status": (
                        short.get("review_status")
                        if isinstance(short, dict) and short.get("review_status")
                        else "pending"
                    ),
                    "platform_targets": (
                        list(short.get("platform_targets"))
                        if isinstance(short, dict) and short.get("platform_targets")
                        else list(data.get("platform_targets") or data.get("target_platforms") or [])
                    ),
                    "publish_status": (
                        short.get("publish_status")
                        if isinstance(short, dict) and short.get("publish_status") is not None
                        else "not_published"
                    ),
                    "retry_count": (
                        int(short.get("retry_count", 0))
                        if isinstance(short, dict)
                        else 0
                    ),
                    "max_retry_attempts": (
                        int(short["max_retry_attempts"])
                        if isinstance(short, dict) and short.get("max_retry_attempts") is not None
                        else None
                    ),
                    "retry_delay_minutes": (
                        int(short["retry_delay_minutes"])
                        if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
                        else None
                    ),
                    "next_retry_at": (
                        short.get("next_retry_at")
                        if isinstance(short, dict)
                        else None
                    ),
                    "last_retry_at": (
                        short.get("last_retry_at")
                        if isinstance(short, dict)
                        else None
                    ),
                    "last_retry_reason": (
                        short.get("last_retry_reason")
                        if isinstance(short, dict)
                        else None
                    ),
                    "retry_status": (
                        short.get("retry_status")
                        if isinstance(short, dict)
                        else None
                    ),
                    "permanently_failed": (
                        bool(short.get("permanently_failed", False))
                        if isinstance(short, dict)
                        else False
                    ),
                    "segment": (
                        {
                            "label": short["segment"].get("label"),
                            "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                            "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                            "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                            "score": float(short["segment"].get("score", 0.0)),
                            "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
                        }
                        if isinstance(short, dict) and isinstance(short.get("segment"), dict)
                        else None
                    ),
                }

                if current_short_id == short_id:
                    current_retry_count = short_data["retry_count"]
                    max_retry_attempts = (
                        short_data["max_retry_attempts"]
                        if short_data["max_retry_attempts"] is not None
                        else get_retry_attempts(data["channel_type"])
                    )
                    retry_delay_minutes = (
                        short_data["retry_delay_minutes"]
                        if short_data["retry_delay_minutes"] is not None
                        else get_retry_delay_minutes(data["channel_type"])
                    )

                    new_retry_count = current_retry_count + 1

                    short_data["retry_count"] = new_retry_count
                    short_data["max_retry_attempts"] = max_retry_attempts
                    short_data["retry_delay_minutes"] = retry_delay_minutes
                    short_data["last_retry_at"] = datetime.now().isoformat()
                    short_data["last_retry_reason"] = str(error_message)

                    if new_retry_count < max_retry_attempts:
                        next_retry_dt = datetime.now() + timedelta(minutes=retry_delay_minutes)
                        short_data["next_retry_at"] = next_retry_dt.strftime("%Y-%m-%d %H:%M")
                        short_data["retry_status"] = "scheduled_retry"
                        short_data["permanently_failed"] = False
                        short_data["publish_status"] = None
                    else:
                        short_data["next_retry_at"] = None
                        short_data["retry_status"] = "permanently_failed"
                        short_data["permanently_failed"] = True
                        short_data["publish_status"] = "failed"

                if short_data["path"]:
                    normalized_shorts.append(short_data)

            data["shorts"] = normalized_shorts
            storage.write_json(job_file, data, indent=4)

            print(f"[Dashboard] Short retry/fail gespeichert: {job_id} / {short_id}")
            return

@app.route("/api/jarvis/alerts")
def jarvis_alerts():
    alerts = _jarvis_monitor.drain_alerts() if _jarvis_monitor else []
    return jsonify({"alerts": alerts})


if __name__ == "__main__":
    _jarvis_monitor = _ProactiveMonitor()
    _jarvis_monitor.start()
    app.run(debug=True)
