"""
jarvis/proactive_monitor.py

JARVIS Proactive Monitor — daemon thread that watches trend signals and
queue state, fires voice alerts, and queues toast notifications for the
dashboard to consume.

Usage:
    monitor = ProactiveMonitor()
    monitor.start()           # starts background daemon thread

    # In Flask route — drain pending alerts:
    alerts = monitor.drain_alerts()  # list[dict], empties the queue
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque

from jarvis.voice_engine import VoiceEngine

_CONFIG_PATH        = Path("data/jarvis_config.json")
_TREND_SIGNALS_PATH = Path("data/trend_signals.json")
_QUEUE_PATH         = Path("data/queue_entries.json")

_DEFAULT_CONFIG: dict = {
    "voice_enabled":         True,
    "alert_interval_minutes": 30,
    "voice_id":              "Antoni",
    "elevenlabs_voice_id":   "ErXwobaYiN019PkySvjV",
}

_STRONG_SIGNAL_MIN  = 0.80   # signal_strength threshold for "viral"
_RECENT_HOURS_MAX   = 2.0    # signals captured within this window count as recent
_VIRAL_COUNT_MIN    = 2      # ≥ N recent strong signals → "trending wave" alert
_MAX_ALERTS_STORED  = 50     # rolling deque cap


class ProactiveMonitor(threading.Thread):
    """
    Daemon thread that checks trend signals and queue state on a
    configurable interval and fires voice + toast alerts.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="JARVIS-ProactiveMonitor")
        self._stop_event   = threading.Event()
        self._alerts: Deque[dict] = deque(maxlen=_MAX_ALERTS_STORED)
        self._seen_signal_ids: set[str] = set()
        self._voice: VoiceEngine | None = None

    # ---------------------------------------------------------------- #
    #  Public                                                            #
    # ---------------------------------------------------------------- #

    def stop(self) -> None:
        """Signal the monitor thread to exit cleanly."""
        self._stop_event.set()

    def drain_alerts(self) -> list[dict]:
        """Return all pending alerts and clear the queue (thread-safe)."""
        result: list[dict] = []
        while self._alerts:
            try:
                result.append(self._alerts.popleft())
            except IndexError:
                break
        return result

    # ---------------------------------------------------------------- #
    #  Thread entry                                                      #
    # ---------------------------------------------------------------- #

    def run(self) -> None:
        print("[JARVIS Monitor] Started.")
        self._voice = self._build_voice_engine()

        while not self._stop_event.is_set():
            try:
                self._run_checks()
            except Exception as exc:
                print(f"[JARVIS Monitor] Check cycle error: {exc}")

            config = self._load_config()
            interval_sec = int(config.get("alert_interval_minutes", 30)) * 60
            self._stop_event.wait(timeout=interval_sec)

        print("[JARVIS Monitor] Stopped.")

    # ---------------------------------------------------------------- #
    #  Check cycle                                                       #
    # ---------------------------------------------------------------- #

    def _run_checks(self) -> None:
        config = self._load_config()
        if not config.get("voice_enabled", True):
            return
        self._check_trend_signals(config)
        self._check_queue_empty(config)

    def _check_trend_signals(self, config: dict) -> None:
        signals = self._load_json(_TREND_SIGNALS_PATH, {}).get("signals", {})
        now     = datetime.now(timezone.utc)

        recent_strong: list[dict] = []
        for sid, sig in signals.items():
            if sid in self._seen_signal_ids:
                continue
            strength = float(sig.get("signal_strength", 0) or 0)
            if strength < _STRONG_SIGNAL_MIN:
                continue
            try:
                captured  = datetime.fromisoformat(sig.get("captured_at", ""))
                age_hours = (now - captured).total_seconds() / 3600
            except (ValueError, TypeError):
                continue
            if age_hours <= _RECENT_HOURS_MAX:
                recent_strong.append(sig)

        if not recent_strong:
            return

        # Mark all as seen so we don't re-alert
        for sig in recent_strong:
            self._seen_signal_ids.add(sig.get("signal_id", ""))

        if len(recent_strong) >= _VIRAL_COUNT_MIN:
            topics  = list({s.get("topic", "Unbekannt") for s in recent_strong})
            primary = topics[0]
            count   = len(recent_strong)
            message = (
                f"Chef, {primary} ist gerade trending. "
                f"{count} Videos in den letzten 2 Stunden viral gegangen."
            )
            self._fire_alert("trend_spike", message, {
                "topics":       topics,
                "signal_count": count,
            })
        else:
            sig      = recent_strong[0]
            topic    = sig.get("topic", "ein Trend")
            strength = float(sig.get("signal_strength", 0))
            message  = (
                f"Neues Trend-Signal: {topic}. "
                f"Signal-Stärke {strength:.0%}. Soll ich einen Job erstellen?"
            )
            self._fire_alert("trend_signal", message, {
                "topic":          topic,
                "signal_strength": strength,
            })

    def _check_queue_empty(self, config: dict) -> None:
        entries = self._load_json(_QUEUE_PATH, {}).get("queue_entries", {})
        active  = [e for e in entries.values() if e.get("queue_state") == "queued"]
        if not active:
            self._fire_alert(
                "queue_empty",
                "Deine Queue ist leer. Zeit für neue Rohvideos.",
                {"queue_count": 0},
            )

    # ---------------------------------------------------------------- #
    #  Alert dispatch                                                    #
    # ---------------------------------------------------------------- #

    def _fire_alert(self, alert_type: str, message: str, meta: dict) -> None:
        print(f"[JARVIS Monitor] ALERT [{alert_type}] {message}")
        alert = {
            "type":      alert_type,
            "message":   message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **meta,
        }
        self._alerts.append(alert)
        if self._voice:
            self._voice.speak(message)

    # ---------------------------------------------------------------- #
    #  Helpers                                                           #
    # ---------------------------------------------------------------- #

    def _load_config(self) -> dict:
        data = self._load_json(_CONFIG_PATH, {})
        return {**_DEFAULT_CONFIG, **data}

    def _build_voice_engine(self) -> VoiceEngine:
        config   = self._load_config()
        voice_id = config.get("elevenlabs_voice_id", _DEFAULT_CONFIG["elevenlabs_voice_id"])
        return VoiceEngine(voice_id=voice_id)

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return default
