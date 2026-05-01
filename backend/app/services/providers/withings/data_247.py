"""Withings 24/7 data sync (sleep, recovery, activity, body composition).

Phase A: all methods stubbed to return empty results so the celery sync
task completes without error. Phase B will implement real Withings API
calls:

- Sleep:        POST /v2/sleep   action=getsummary
- Recovery/HR:  POST /v2/heart   action=list
- Activity:     POST /v2/measure action=getintradayactivity
- Daily totals: POST /v2/measure action=getactivity
- Body comp:    POST /measure    action=getmeas
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.database import DbSession
from app.services.providers.templates.base_247_data import Base247DataTemplate

logger = logging.getLogger(__name__)


class Withings247Data(Base247DataTemplate):
    """Withings 24/7 data — Phase A stubs return empty lists."""

    # ---- Sleep -------------------------------------------------------

    def get_sleep_data(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        logger.info("Withings get_sleep_data Phase A stub — user_id=%s", user_id)
        return []

    def normalize_sleep(self, raw_sleep: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        # Phase A unreachable (get_sleep_data returns []).
        raise NotImplementedError("Withings normalize_sleep — Phase B")

    # ---- Recovery ----------------------------------------------------

    def get_recovery_data(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        logger.info("Withings get_recovery_data Phase A stub — user_id=%s", user_id)
        return []

    def normalize_recovery(self, raw_recovery: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        raise NotImplementedError("Withings normalize_recovery — Phase B")

    # ---- Activity samples (HR, steps, etc.) --------------------------

    def get_activity_samples(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        logger.info("Withings get_activity_samples Phase A stub — user_id=%s", user_id)
        return []

    def normalize_activity_samples(
        self,
        raw_samples: list[dict[str, Any]],
        user_id: UUID,
    ) -> dict[str, list[dict[str, Any]]]:
        # Default empty buckets so downstream consumers don't KeyError.
        return {"heart_rate": [], "steps": [], "spo2": []}

    # ---- Daily activity ---------------------------------------------

    def get_daily_activity_statistics(
        self,
        db: DbSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        logger.info("Withings get_daily_activity_statistics Phase A stub — user_id=%s", user_id)
        return []

    def normalize_daily_activity(self, raw_stats: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        raise NotImplementedError("Withings normalize_daily_activity — Phase B")
