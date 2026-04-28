from datetime import datetime


class Scheduler:
    def is_due(self, scheduled_at: str | None) -> bool:
        if not scheduled_at:
            return False

        scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")
        now = datetime.now()
        return now >= scheduled_dt