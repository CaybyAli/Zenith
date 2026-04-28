from __future__ import annotations

from core.trend_qualification_store import TrendQualificationStore
from core.trend_qualifier import TrendQualifier
from core.trend_store import TrendStore
from models.trend_qualification import TrendQualification
from shared.errors import ValidationError


class TrendQualificationManager:
    def __init__(
        self,
        trend_store: TrendStore,
        qualification_store: TrendQualificationStore,
        trend_qualifier: TrendQualifier | None = None,
    ) -> None:
        self.trend_store = trend_store
        self.qualification_store = qualification_store
        self.trend_qualifier = trend_qualifier or TrendQualifier()

    def qualify_signal(self, signal_id: str) -> TrendQualification:
        if not signal_id or not signal_id.strip():
            raise ValidationError("signal_id is required")

        signal = self.trend_store.get_signal(signal_id)
        qualification = self.trend_qualifier.qualify(signal)
        return self.qualification_store.create_qualification(qualification)