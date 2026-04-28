# TODO: Backlog Phase 2 — Director Engine ist aktuell nicht in Pipeline integriert.
# Soll spaeter als pipeline stage 4 angeschlossen werden.
"""
core/director_engine.py — Zenith Auto-Director (pipeline stage 4).

Analyzes a 3840x1080 (32:9) OBS recording with embedded facecam overlay,
makes frame-by-frame composition decisions, and renders a final 1920x1080
directed video with dynamic facecam placement.

Source layout:
  x=0–500     : Facecam overlay (embedded by OBS)
  x=1920–3840 : Gameplay (right half, 1920x1080 effective)

Output modes (applied per 0.5s window):
  facecam_large   — facecam 768x432 bottom-left, gameplay behind
  gameplay_zoomed — gameplay only, 1.15x zoom to action center
  facecam_small   — facecam 280x180 top-left, gameplay behind (default)

Run directly:
  python -m core.director_engine

Or import run_director() for programmatic use.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from moviepy.editor import CompositeVideoClip, VideoFileClip, concatenate_videoclips

# ------------------------------------------------------------------ #
#  Source / output geometry constants                                  #
# ------------------------------------------------------------------ #

_SRC_W = 3840
_SRC_H = 1080

_FACECAM_X_END = 500       # facecam region: x=0 to x=500 in source
_GAMEPLAY_X_START = 1920   # gameplay region: x=1920 to x=3840 in source

_OUT_W = 1920
_OUT_H = 1080

# Facecam overlay dimensions in output frame
_FC_SMALL_W, _FC_SMALL_H = 280, 180
_FC_LARGE_W, _FC_LARGE_H = 768, 432   # 40% of output width, 16:9

# ------------------------------------------------------------------ #
#  Analysis tuning                                                     #
# ------------------------------------------------------------------ #

_CHUNK_DURATION = 0.5        # seconds per analysis window
_AUDIO_FPS = 22050
_AUDIO_RMS_HIGH = 0.05       # RMS above this = high speaker energy
_GAMEPLAY_MOTION_HIGH = 8.0  # mean pixel diff above this = action
_FACECAM_MOTION_ACTIVE = 5.0 # mean pixel diff in facecam region = speaker active

# ------------------------------------------------------------------ #
#  Render                                                              #
# ------------------------------------------------------------------ #

_TRANSITION_DURATION = 0.2   # seconds for crossfade between mode changes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
#  Data model                                                          #
# ------------------------------------------------------------------ #

@dataclass
class DirectorCue:
    time: float
    duration: float
    mode: str          # "facecam_large" | "gameplay_zoomed" | "facecam_small"
    facecam_size: str  # "large" | "small" | "hidden"
    game_zoom: float   # 1.0 or 1.15
    transition: str    # "smooth" | "cut"

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ #
#  DirectorEngine                                                      #
# ------------------------------------------------------------------ #

class DirectorEngine:

    # ---------------------------------------------------------------- #
    #  Public API                                                        #
    # ---------------------------------------------------------------- #

    def analyze(self, video_path: str) -> list[DirectorCue]:
        """
        Analyze video and return a list of DirectorCues.
        Each cue covers a contiguous run of the same composition mode.
        """
        print(f"[director] ANALYZE    {video_path}")

        audio_rms = self._extract_audio_rms(video_path)
        motion = self._extract_motion(video_path)
        n = max(len(audio_rms), len(motion))

        if n == 0:
            print("[director] WARN       no signal data — single fallback cue")
            return [DirectorCue(
                time=0.0, duration=0.0, mode="facecam_small",
                facecam_size="small", game_zoom=1.0, transition="cut",
            )]

        # Build per-chunk mode decisions, then merge consecutive runs
        cues: list[DirectorCue] = []
        seg_start = 0.0
        seg_mode: str | None = None

        for i in range(n):
            rms = audio_rms[i] if i < len(audio_rms) else 0.0
            gm = motion[i]["gameplay"] if i < len(motion) else 0.0
            fm = motion[i]["facecam"] if i < len(motion) else 0.0
            mode = self._decide_mode(rms, gm, fm)

            if mode != seg_mode:
                if seg_mode is not None:
                    cues.append(self._make_cue(seg_start, i * _CHUNK_DURATION, seg_mode))
                seg_start = i * _CHUNK_DURATION
                seg_mode = mode

        # Flush the final run
        if seg_mode is not None:
            cues.append(self._make_cue(seg_start, n * _CHUNK_DURATION, seg_mode))

        print(f"[director] CUES       {len(cues)} cue(s) generated")
        for c in cues:
            print(
                f"[director]   {c.time:6.1f}s  +{c.duration:.1f}s"
                f"  {c.mode}  zoom={c.game_zoom}"
            )
        return cues

    def render(
        self,
        video_path: str,
        cues: list[DirectorCue],
        output_path: str,
    ) -> None:
        """
        Apply DirectorCues to the video and write a 1920x1080 MP4.
        Smooth 0.2s crossfade between mode changes; falls back to hard cuts.
        """
        print(f"[director] RENDER     {video_path}  cues={len(cues)}")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        source = VideoFileClip(str(video_path))
        try:
            clips = []
            for cue in cues:
                t_end = min(cue.time + cue.duration, source.duration)
                if t_end <= cue.time:
                    continue
                segment = source.subclip(cue.time, t_end)
                clips.append(self._compose_segment(segment, cue))

            if not clips:
                raise ValueError("No renderable cues")

            # Smooth transitions
            try:
                faded = [clips[0]]
                for clip in clips[1:]:
                    faded.append(clip.crossfadein(_TRANSITION_DURATION))
                final = concatenate_videoclips(
                    faded,
                    method="compose",
                    padding=-_TRANSITION_DURATION,
                )
            except Exception as exc:
                print(f"[director] WARN       crossfade failed ({exc}) — hard cuts")
                final = concatenate_videoclips(clips, method="compose")

            print(f"[director] WRITE      {output_path}  ({final.duration:.1f}s total)")
            final.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
        finally:
            source.close()

        print(f"[director] DONE       {output_path}")

    # ---------------------------------------------------------------- #
    #  Analysis helpers                                                  #
    # ---------------------------------------------------------------- #

    def _extract_audio_rms(self, video_path: str) -> list[float]:
        """
        RMS per _CHUNK_DURATION window.
        All frames loaded at once — no start_time/end_time in iter_frames().
        """
        clip = VideoFileClip(str(video_path))
        audio = clip.audio

        if audio is None:
            clip.close()
            return []

        all_frames = list(audio.iter_frames(fps=_AUDIO_FPS))
        clip.close()

        frames_per_chunk = int(_AUDIO_FPS * _CHUNK_DURATION)
        rms_list: list[float] = []

        for i in range(0, len(all_frames) - frames_per_chunk, frames_per_chunk):
            arr = np.array(all_frames[i:i + frames_per_chunk])
            rms_list.append(float(np.sqrt(np.mean(arr ** 2))))

        return rms_list

    def _extract_motion(self, video_path: str) -> list[dict]:
        """
        Per-chunk motion signals: {"gameplay": float, "facecam": float}.
        Samples one frame per _CHUNK_DURATION using cv2; uses cv2.absdiff
        between consecutive sample frames to measure pixel-level change.
        Region boundaries are computed proportionally so the method works
        even if cv2 decodes at a different resolution.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_per_chunk = max(1, int(src_fps * _CHUNK_DURATION))

        signals: list[dict] = []
        prev_facecam: np.ndarray | None = None
        prev_gameplay: np.ndarray | None = None
        chunk_idx = 0

        while True:
            frame_pos = chunk_idx * frames_per_chunk
            if frame_pos >= total_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_pos))
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # Scale region boundaries proportionally to decoded frame width
            fc_end = max(1, int(w * _FACECAM_X_END / _SRC_W))
            gp_start = min(int(w * _GAMEPLAY_X_START / _SRC_W), w - 1)

            facecam_region = gray[:, :fc_end]
            gameplay_region = gray[:, gp_start:]

            if prev_facecam is not None:
                fc_diff = float(np.mean(cv2.absdiff(facecam_region, prev_facecam)))
                gp_diff = float(np.mean(cv2.absdiff(gameplay_region, prev_gameplay)))
            else:
                fc_diff = 0.0
                gp_diff = 0.0

            signals.append({"gameplay": gp_diff, "facecam": fc_diff})
            prev_facecam = facecam_region
            prev_gameplay = gameplay_region
            chunk_idx += 1

        cap.release()
        return signals

    # ---------------------------------------------------------------- #
    #  Decision logic                                                    #
    # ---------------------------------------------------------------- #

    def _decide_mode(
        self,
        audio_rms: float,
        gameplay_motion: float,
        facecam_motion: float,
    ) -> str:
        # Priority 1 — high speaker energy AND face is moving → facecam_large
        if audio_rms > _AUDIO_RMS_HIGH and facecam_motion > _FACECAM_MOTION_ACTIVE:
            return "facecam_large"

        # Priority 2 — fast gameplay action / sudden movement → gameplay_zoomed
        if gameplay_motion > _GAMEPLAY_MOTION_HIGH:
            return "gameplay_zoomed"

        # Priority 3 — quiet moment, small reminder that creator is present
        return "facecam_small"

    # ---------------------------------------------------------------- #
    #  Render helpers                                                    #
    # ---------------------------------------------------------------- #

    def _compose_segment(self, segment: VideoFileClip, cue: DirectorCue):
        """
        Build a single 1920x1080 CompositeVideoClip for one DirectorCue segment.
        Crops gameplay from the right half of the source frame.
        """
        src_w = segment.w

        # Extract gameplay (right half) and scale to output size
        gp_x = max(0, int(src_w * _GAMEPLAY_X_START / _SRC_W))
        gameplay = segment.crop(x1=gp_x).resize((_OUT_W, _OUT_H))

        if cue.mode == "gameplay_zoomed":
            # Crop centre to 1/zoom size, then scale back up
            z = cue.game_zoom  # 1.15
            cw = int(_OUT_W / z)
            ch = int(_OUT_H / z)
            x_off = (_OUT_W - cw) // 2
            y_off = (_OUT_H - ch) // 2
            return gameplay.crop(x1=x_off, y1=y_off, width=cw, height=ch).resize((_OUT_W, _OUT_H))

        # Extract facecam from left region
        fc_x_end = max(1, int(src_w * _FACECAM_X_END / _SRC_W))
        facecam_raw = segment.crop(x1=0, x2=fc_x_end)

        if cue.mode == "facecam_large":
            facecam = facecam_raw.resize((_FC_LARGE_W, _FC_LARGE_H))
            pos = (0, _OUT_H - _FC_LARGE_H)  # bottom-left
        else:  # facecam_small
            facecam = facecam_raw.resize((_FC_SMALL_W, _FC_SMALL_H))
            pos = (0, 0)  # top-left

        return CompositeVideoClip(
            [gameplay, facecam.set_position(pos)],
            size=(_OUT_W, _OUT_H),
        )

    # ---------------------------------------------------------------- #
    #  Internal factory                                                  #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _make_cue(t_start: float, t_end: float, mode: str) -> DirectorCue:
        facecam_size = (
            "large" if mode == "facecam_large"
            else "hidden" if mode == "gameplay_zoomed"
            else "small"
        )
        return DirectorCue(
            time=t_start,
            duration=max(0.0, t_end - t_start),
            mode=mode,
            facecam_size=facecam_size,
            game_zoom=1.15 if mode == "gameplay_zoomed" else 1.0,
            transition="smooth",
        )


# ------------------------------------------------------------------ #
#  Batch dispatcher                                                    #
# ------------------------------------------------------------------ #

def run_director(jobs_path: str = "data/jobs.json") -> list[dict]:
    """
    Process all assembled jobs: analyze → render → save director_cues.json.
    Returns a list of result dicts: {"job_id": ..., "status": "ok"|"error", ...}
    """
    path = Path(jobs_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs_map: dict = data["jobs"]

    pending = [
        job for job in jobs_map.values()
        if job.get("status") == "assembled"
        and job.get("video_path")
    ]

    print(f"[director] {len(pending)} assembled job(s) found")

    engine = DirectorEngine()
    results: list[dict] = []

    for job in pending:
        job_id = job["job_id"]
        video_path = job["video_path"]

        # Mark in-progress
        job["status"] = "directing"
        job["updated_at"] = _utc_now()
        jobs_map[job_id] = job
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"[director] START      {job_id}  video={video_path!r}")

        try:
            cues = engine.analyze(video_path)

            out_dir = Path("output/directed") / job_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = str(out_dir / "final_directed.mp4")

            engine.render(video_path, cues, out_file)

            # Save cues as JSON for dashboard preview
            cues_path = out_dir / "director_cues.json"
            cues_path.write_text(
                json.dumps(
                    {"job_id": job_id, "cues": [c.to_dict() for c in cues]},
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"[director] CUES JSON  {job_id}  → {cues_path}")

            job["status"] = "directed"
            job["video_path"] = out_file
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            results.append({"job_id": job_id, "status": "ok", "output": out_file})

        except Exception as exc:
            job["status"] = "direction_failed"
            job["error_message"] = str(exc)
            job["updated_at"] = _utc_now()
            jobs_map[job_id] = job

            print(f"[director] ERROR      {job_id}  {exc}")
            results.append({"job_id": job_id, "status": "error", "error": str(exc)})

        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return results


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    results = run_director()

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    print(f"\n[director] Done — ok={ok}  failed={failed}")

    for r in results:
        icon = "✓" if r["status"] == "ok" else "✗"
        print(f"  {icon}  {r['job_id']}")
        if r["status"] == "error":
            print(f"       {r['error']}")

    sys.exit(0 if failed == 0 else 1)
