"""Withings workout sync.

Phase A: stub. Returns no workouts so the celery sync task completes
without error. Phase B will call ``/v2/measure action=getworkouts`` and
normalize into ``EventRecord`` rows.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.database import DbSession
from app.schemas.model_crud.activities import EventRecordCreate, EventRecordDetailCreate
from app.services.providers.templates.base_workouts import BaseWorkoutsTemplate

logger = logging.getLogger(__name__)


class WithingsWorkouts(BaseWorkoutsTemplate):
    """Withings workouts via /v2/measure action=getworkouts. Phase A: empty stub."""

    def get_workouts(
        self,
        db: DbSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Any]:
        # TODO Phase B: POST to /v2/measure with action=getworkouts,
        # paginate via more/offset, return raw workout dicts.
        logger.info(
            "WithingsWorkouts.get_workouts is a Phase A stub — returning []. "
            "user_id=%s start=%s end=%s",
            user_id,
            start_date,
            end_date,
        )
        return []

    def _normalize_workout(
        self,
        raw_workout: Any,
        user_id: UUID,
    ) -> tuple[EventRecordCreate, EventRecordDetailCreate]:
        # TODO Phase B: map Withings category int → UnifiedWorkoutType,
        # extract HR/distance/calories/elevation from raw_workout.data,
        # set external_id=str(raw_workout["id"]).
        raise NotImplementedError("WithingsWorkouts._normalize_workout is a Phase A stub")

    def load_data(self, db: DbSession, user_id: UUID, **kwargs: Any) -> int:
        # TODO Phase B: full sync. For now report zero records loaded so the
        # celery sync task can proceed without crashing.
        logger.info(
            "WithingsWorkouts.load_data is a Phase A stub — returning 0. user_id=%s",
            user_id,
        )
        return 0
