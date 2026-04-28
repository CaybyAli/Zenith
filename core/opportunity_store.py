from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.opportunity import Opportunity
from shared.errors import NotFoundError, StorageError


class OpportunityStore:
    def __init__(
        self,
        opportunities_path: str = "data/opportunities.json",
    ) -> None:
        self.opportunities_path = Path(opportunities_path)
        self.opportunities_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.opportunities_path.exists():
            self._write_raw({"opportunities": {}})

    def create_opportunity(self, opportunity: Opportunity) -> Opportunity:
        data = self._read_raw()
        opportunities = data["opportunities"]

        for existing in opportunities.values():
            existing_opportunity = Opportunity.from_dict(existing)
            if existing_opportunity.qualification_id == opportunity.qualification_id:
                return existing_opportunity

        if opportunity.opportunity_id in opportunities:
            raise StorageError(f"Opportunity already exists: {opportunity.opportunity_id}")

        opportunities[opportunity.opportunity_id] = opportunity.to_dict()
        self._write_raw(data)
        return opportunity

    def update_opportunity(self, opportunity: Opportunity) -> Opportunity:
        data = self._read_raw()
        opportunities = data["opportunities"]

        if opportunity.opportunity_id not in opportunities:
            raise NotFoundError(f"Opportunity not found: {opportunity.opportunity_id}")

        opportunity.touch()
        opportunities[opportunity.opportunity_id] = opportunity.to_dict()
        self._write_raw(data)
        return opportunity

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        data = self._read_raw()
        opportunities = data["opportunities"]

        if opportunity_id not in opportunities:
            raise NotFoundError(f"Opportunity not found: {opportunity_id}")

        return Opportunity.from_dict(opportunities[opportunity_id])

    def get_by_qualification_id(self, qualification_id: str) -> Opportunity:
        data = self._read_raw()
        opportunities = data["opportunities"]

        for item in opportunities.values():
            opportunity = Opportunity.from_dict(item)
            if opportunity.qualification_id == qualification_id:
                return opportunity

        raise NotFoundError(f"Opportunity not found for qualification_id: {qualification_id}")

    def list_opportunities(self) -> list[Opportunity]:
        data = self._read_raw()
        return [Opportunity.from_dict(item) for item in data["opportunities"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.opportunities_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read opportunity store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.opportunities_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write opportunity store: {exc}") from exc