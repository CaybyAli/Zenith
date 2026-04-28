from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.trend_qualification import TrendQualification
from shared.errors import NotFoundError, StorageError


class TrendQualificationStore:
    def __init__(
        self,
        qualifications_path: str = "data/trend_qualifications.json",
    ) -> None:
        self.qualifications_path = Path(qualifications_path)
        self.qualifications_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.qualifications_path.exists():
            self._write_raw({"qualifications": {}})

    def create_qualification(self, qualification: TrendQualification) -> TrendQualification:
        data = self._read_raw()
        qualifications = data["qualifications"]

        for existing in qualifications.values():
            existing_qualification = TrendQualification.from_dict(existing)
            if existing_qualification.signal_id == qualification.signal_id:
                return existing_qualification

        if qualification.qualification_id in qualifications:
            raise StorageError(f"Trend qualification already exists: {qualification.qualification_id}")

        qualifications[qualification.qualification_id] = qualification.to_dict()
        self._write_raw(data)
        return qualification

    def update_qualification(self, qualification: TrendQualification) -> TrendQualification:
        data = self._read_raw()
        qualifications = data["qualifications"]

        if qualification.qualification_id not in qualifications:
            raise NotFoundError(f"Trend qualification not found: {qualification.qualification_id}")

        qualification.touch()
        qualifications[qualification.qualification_id] = qualification.to_dict()
        self._write_raw(data)
        return qualification

    def get_qualification(self, qualification_id: str) -> TrendQualification:
        data = self._read_raw()
        qualifications = data["qualifications"]

        if qualification_id not in qualifications:
            raise NotFoundError(f"Trend qualification not found: {qualification_id}")

        return TrendQualification.from_dict(qualifications[qualification_id])

    def get_by_signal_id(self, signal_id: str) -> TrendQualification:
        data = self._read_raw()
        qualifications = data["qualifications"]

        for item in qualifications.values():
            qualification = TrendQualification.from_dict(item)
            if qualification.signal_id == signal_id:
                return qualification

        raise NotFoundError(f"Trend qualification not found for signal_id: {signal_id}")

    def list_qualifications(self) -> list[TrendQualification]:
        data = self._read_raw()
        return [TrendQualification.from_dict(item) for item in data["qualifications"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.qualifications_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read trend qualification store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.qualifications_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write trend qualification store: {exc}") from exc