"""Helper for Withings data-endpoint POSTs.

Withings' data API is form-body-only and returns
``{"status": 0, "body": {...}}`` envelopes. This module wraps the auth
boilerplate and envelope-unwrap so callers can think in terms of
``post_action(endpoint, action, **params) -> dict``.

Authorization is via ``Authorization: Bearer <access_token>``.
"""

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from app.database import DbSession
from app.repositories.user_connection_repository import UserConnectionRepository
from app.services.providers.templates.base_oauth import BaseOAuthTemplate
from app.utils.structured_logging import log_structured

logger = logging.getLogger(__name__)


def _unwrap(response_json: dict, *, provider: str, action: str) -> dict:
    status = response_json.get("status")
    if status != 0:
        error = response_json.get("error", "unknown")
        log_structured(
            logger,
            "error",
            f"Withings API non-zero status for {action}: {status} ({error})",
            provider=provider,
            task=action,
            status=status,
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Withings API error (status={status}, action={action}): {error}",
        )
    body = response_json.get("body")
    return body if isinstance(body, dict) else {}


def post_withings_action(
    db: DbSession,
    user_id: UUID,
    connection_repo: UserConnectionRepository,
    oauth: BaseOAuthTemplate,
    api_base_url: str,
    endpoint: str,
    action: str,
    params: dict[str, Any] | None = None,
) -> dict:
    """POST to a Withings endpoint with action= and bearer token.

    Args:
        endpoint: e.g. "/v2/sleep" — concatenated to api_base_url.
        action: e.g. "getsummary" — added to the form body.
        params: extra form fields (startdateymd, enddateymd, data_fields, etc.).

    Returns:
        The unwrapped ``body`` dict from the Withings response. ``{}`` if no body.

    Refreshes access token on 401 / expired-token error and retries once.
    """
    connection = connection_repo.get_by_user_and_provider(db, user_id, oauth.provider_name)
    if connection is None or not connection.access_token:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"No active {oauth.provider_name} connection for user",
        )

    form_body: dict[str, Any] = {"action": action}
    if params:
        form_body.update(params)

    def _do_post(token: str) -> httpx.Response:
        return httpx.post(
            f"{api_base_url}{endpoint}",
            data=form_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30.0,
        )

    response = _do_post(connection.access_token)

    # Withings returns 200 even on auth failures — must inspect status field.
    json_data = response.json()
    if json_data.get("status") in (401, 601):  # 401 unauthorized, 601 auth failed
        log_structured(
            logger,
            "info",
            f"Withings access token expired (status={json_data.get('status')}), refreshing",
            provider=oauth.provider_name,
            task="post_withings_action",
            user_id=str(user_id),
        )
        if not connection.refresh_token:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No refresh_token to retry with")
        token_response = oauth.refresh_access_token(db, user_id, connection.refresh_token)
        response = _do_post(token_response.access_token)
        json_data = response.json()

    response.raise_for_status()
    return _unwrap(json_data, provider=oauth.provider_name, action=action)
