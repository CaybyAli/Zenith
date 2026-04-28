"""
jarvis/voice_engine.py

JARVIS Text-to-Speech engine.

Priority order:
  1. ElevenLabs API  (if ELEVENLABS_API_KEY is set)
  2. pyttsx3         (offline fallback, always available)

Usage:
    from jarvis.voice_engine import VoiceEngine
    VoiceEngine().speak("Chef, alles läuft.")

speak() is non-blocking by default — audio plays in a daemon thread.
Set blocking=True for synchronous use (e.g. tests).
"""
from __future__ import annotations

import os
import tempfile
import threading

import requests

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
_MODEL_ID = "eleven_multilingual_v2"

# Well-known ElevenLabs voice name → voice_id aliases
_VOICE_ALIASES: dict[str, str] = {
    "Antoni":  "ErXwobaYiN019PkySvjV",
    "Antoni ": "ErXwobaYiN019PkySvjV",
    "Rachel":  "21m00Tcm4TlvDq8ikWAM",
    "Domi":    "AZnzlk1XvdvUeBnXmlld",
    "Bella":   "EXAVITQu4vr4xnSDxMaL",
    "Adam":    "pNInz6obpgDQGcFmaJgB",
    "Sam":     "yoZ06aMxZJJ28mfd3POQ",
}
_DEFAULT_VOICE_ID = _VOICE_ALIASES["Antoni"]


def _resolve_voice_id(voice: str) -> str:
    """Return raw ElevenLabs voice_id, resolving friendly names."""
    return _VOICE_ALIASES.get(voice.strip(), voice.strip()) or _DEFAULT_VOICE_ID


class VoiceEngine:
    """Thread-safe TTS engine. speak() fires a daemon thread by default."""

    def __init__(
        self,
        voice_id: str | None = None,
        api_key: str | None = None,
        blocking: bool = False,
    ) -> None:
        self._api_key = (api_key or os.environ.get("ELEVENLABS_API_KEY", "")).strip()
        raw = voice_id or _DEFAULT_VOICE_ID
        self._voice_id = _resolve_voice_id(raw)
        self._blocking = blocking
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- #
    #  Public API                                                        #
    # ---------------------------------------------------------------- #

    def speak(self, text: str) -> None:
        """Speak *text*. Non-blocking unless self._blocking is True."""
        text = text.strip()
        if not text:
            return
        if self._blocking:
            self._speak_sync(text)
        else:
            t = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            t.start()

    # ---------------------------------------------------------------- #
    #  Internal                                                          #
    # ---------------------------------------------------------------- #

    def _speak_sync(self, text: str) -> None:
        with self._lock:
            if self._api_key:
                try:
                    self._speak_elevenlabs(text)
                    return
                except Exception as exc:
                    print(f"[VoiceEngine] ElevenLabs failed ({exc}); using pyttsx3")
            self._speak_pyttsx3(text)

    def _speak_elevenlabs(self, text: str) -> None:
        url = f"{_ELEVENLABS_BASE}/{self._voice_id}"
        payload = {
            "text": text,
            "model_id": _MODEL_ID,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
        }
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        self._play_audio(resp.content)

    def _play_audio(self, data: bytes) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
            fh.write(data)
            tmp_path = fh.name
        try:
            self._play_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _play_file(self, path: str) -> None:
        """Play audio file: pygame → playsound → Windows shell."""
        try:
            import pygame  # type: ignore[import]
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            import time
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            return
        except Exception:
            pass

        try:
            from playsound import playsound  # type: ignore[import]
            playsound(path, block=True)
            return
        except Exception:
            pass

        try:
            import subprocess
            subprocess.run(
                ["cmd", "/c", "start", "/wait", "", path],
                check=False,
                capture_output=True,
            )
        except Exception as exc:
            print(f"[VoiceEngine] Could not play audio: {exc}")

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            import pyttsx3  # type: ignore[import]
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            print(f"[VoiceEngine] pyttsx3 failed: {exc}")
