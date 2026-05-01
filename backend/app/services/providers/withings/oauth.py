"""Withings OAuth 2.0 implementation.

Withings violates RFC 6749 in three ways that the BaseOAuthTemplate doesn't
handle out-of-the-box:

1.  The token endpoint requires an ``action=requesttoken`` form field on both
    initial code exchange and refresh.
2.  Successful token responses are wrapped: ``{"status": 0, "body": {...}}``
    rather than the body fields at the top level. We must unwrap and verify
    ``status == 0`` before validating against ``OAuthTokenResponse``.
3.  Client credentials must travel in the request body — Withings rejects
    Basic Auth.

We override ``_exchange_token`` and ``refresh_access_token`` (rather than
just ``_prepare_*``) because the unwrap has to happen between
``response.json()`` and ``OAuthTokenResponse.model_validate``. Everything
else inherits cleanly.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.config import settings
from app.database import DbSession
from app.schemas.auth import AuthenticationMethod
from app.schemas.enums import ProviderName
from app.schemas.model_crud.credentials import (
    OAuthTokenResponse,
    ProviderCredentials,
    ProviderEndpoints,
)
from app.services.providers.templates.base_oauth import BaseOAuthTemplate
from app.utils.structured_logging import log_structured

logger = logging.getLogger(__name__)


class WithingsOAuth(BaseOAuthTemplate):
    """Withings OAuth 2.0 implementation with body-only auth + wrapped responses."""

    @property
    def endpoints(self) -> ProviderEndpoints:
        return ProviderEndpoints(
            authorize_url="https://account.withings.com/oauth2_user/authorize2",
            token_url="https://wbsapi.withings.net/v2/oauth2",
        )

    @property
    def credentials(self) -> ProviderCredentials:
        return ProviderCredentials(
            client_id=settings.withings_client_id or "",
            client_secret=(settings.withings_client_secret.get_secret_value() if settings.withings_client_secret else ""),
            redirect_uri=settings.oauth_redirect_uri(ProviderName.WITHINGS),
            default_scope=settings.withings_default_scope,
        )

    use_pkce: bool = False
    auth_method: AuthenticationMethod = AuthenticationMethod.BODY

    # ------------------------------------------------------------------
    # Quirk 1: action= field on both initial exchange and refresh
    # ------------------------------------------------------------------

    def _prepare_token_request(self, code: str, code_verifier: str | None) -> tuple[dict, dict]:
        data, headers = super()._prepare_token_request(code, code_verifier)
        data["action"] = "requesttoken"
        return data, headers

    def _prepare_refresh_request(self, refresh_token: str) -> tuple[dict, dict]:
        data, headers = super()._prepare_refresh_request(refresh_token)
        data["action"] = "requesttoken"
        return data, headers

    # ------------------------------------------------------------------
    # Quirk 2: response is wrapped — must unwrap body and check status
    # ------------------------------------------------------------------

    def _unwrap_token_response(self, response_json: dict) -> dict:
        """Unwrap Withings' {"status": 0, "body": {...}} envelope.

        Raises HTTPException on non-zero status.
        """
        status = response_json.get("status")
        if status != 0:
            error = response_json.get("error", "unknown")
            log_structured(
                logger,
                "error",
                f"Withings token endpoint returned non-zero status: {status} ({error})",
                provider=self.provider_name,
                task="unwrap_token_response",
                status=status,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Withings OAuth error (status={status}): {error}",
            )
        body = response_json.get("body")
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Withings token response missing 'body' object",
            )
        return body

    def _exchange_token(self, code: str, code_verifier: str | None) -> OAuthTokenResponse:
        """Override to unwrap Withings' wrapped response."""
        data, headers = self._prepare_token_request(code, code_verifier)

        try:
            response = httpx.post(
                self.endpoints.token_url,
                data=data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            body = self._unwrap_token_response(response.json())
            return OAuthTokenResponse.model_validate(body)
        except httpx.HTTPStatusError as e:
            log_structured(
                logger,
                "error",
                f"Failed to exchange Withings authorization code: {e.response.text}",
                provider=self.provider_name,
                task="exchange_token",
                status_code=e.response.status_code,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange authorization code: {e.response.text}",
            )

    def refresh_access_token(self, db: DbSession, user_id: UUID, refresh_token: str) -> OAuthTokenResponse:
        """Override to unwrap response. Otherwise mirrors base template logic."""
        data, headers = self._prepare_refresh_request(refresh_token)

        try:
            response = httpx.post(
                self.endpoints.token_url,
                data=data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            body = self._unwrap_token_response(response.json())
            token_response = OAuthTokenResponse.model_validate(body)

            connection = self.connection_repo.get_by_user_and_provider(db, user_id, self.provider_name)
            if connection:
                self.connection_repo.update_tokens(
                    db,
                    connection,
                    token_response.access_token,
                    # Withings rotates refresh tokens on every refresh — always prefer the new one.
                    token_response.refresh_token or refresh_token,
                    token_response.expires_in,
                )

            log_structured(
                logger,
                "info",
                "OAuth token refreshed successfully",
                provider=self.provider_name,
                task="refresh_access_token",
                user_id=str(user_id),
            )

            return token_response

        except httpx.HTTPStatusError as e:
            log_structured(
                logger,
                "error",
                f"Failed to refresh Withings token: {e.response.text}",
                provider=self.provider_name,
                task="refresh_access_token",
                user_id=str(user_id),
                status_code=e.response.status_code,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh token: {e.response.text}",
            )

    # ------------------------------------------------------------------
    # provider_user_id comes free in the token response body — no extra
    # API call needed (the base default returns None/None, which is fine,
    # but we can do better).
    # ------------------------------------------------------------------

    def _get_provider_user_info(self, token_response: OAuthTokenResponse, user_id: str) -> dict[str, str | None]:
        # OAuthTokenResponse is the validated `body` — Withings includes `userid` there.
        # If model_validate dropped the field, fall back to None.
        provider_user_id = getattr(token_response, "userid", None) or getattr(token_response, "user_id", None)
        if provider_user_id is not None:
            provider_user_id = str(provider_user_id)
        return {"user_id": provider_user_id, "username": None}
