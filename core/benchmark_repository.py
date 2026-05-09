"""
BenchmarkRepository — speichert und lädt BenchmarkSessions als JSON.

Speicherort: storage/benchmarks/<job_id>/<session_id>.json
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional
from models.benchmark_session import BenchmarkSession

logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK_DIR = Path("storage") / "benchmarks"


class BenchmarkRepository:

    def __init__(self, base_dir: Path = DEFAULT_BENCHMARK_DIR):
        self.base_dir = base_dir

    def _session_path(self, session: BenchmarkSession) -> Path:
        job_dir = self.base_dir / session.job_id
        return job_dir / f"{session.session_id}.json"

    def save(self, session: BenchmarkSession) -> Path:
        path = self._session_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(
            f"[BenchmarkRepository] SAVED session={session.session_id} "
            f"job={session.job_id} entries={len(session.entries)} "
            f"score={session.quality_score():.4f} path={path}"
        )
        return path

    def load(self, job_id: str, session_id: str) -> Optional[BenchmarkSession]:
        path = self.base_dir / job_id / f"{session_id}.json"
        if not path.exists():
            logger.warning(f"[BenchmarkRepository] NOT FOUND session={session_id} job={job_id}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session = BenchmarkSession.from_dict(data)
        logger.info(
            f"[BenchmarkRepository] LOADED session={session.session_id} "
            f"job={session.job_id} entries={len(session.entries)}"
        )
        return session

    def list_sessions_for_job(self, job_id: str) -> List[BenchmarkSession]:
        job_dir = self.base_dir / job_id
        if not job_dir.exists():
            return []
        sessions = []
        for path in sorted(job_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(BenchmarkSession.from_dict(data))
            except Exception as e:
                logger.warning(f"[BenchmarkRepository] SKIP {path}: {e}")
        return sessions

    def list_all_sessions(self) -> List[BenchmarkSession]:
        if not self.base_dir.exists():
            return []
        sessions = []
        for job_dir in sorted(self.base_dir.iterdir()):
            if job_dir.is_dir():
                sessions.extend(self.list_sessions_for_job(job_dir.name))
        return sessions

    def delete(self, job_id: str, session_id: str) -> bool:
        path = self.base_dir / job_id / f"{session_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"[BenchmarkRepository] DELETED session={session_id} job={job_id}")
            return True
        return False
