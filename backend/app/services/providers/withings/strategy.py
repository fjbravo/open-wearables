from app.services.providers.base_strategy import BaseProviderStrategy, ProviderCapabilities
from app.services.providers.withings.data_247 import Withings247Data
from app.services.providers.withings.oauth import WithingsOAuth
from app.services.providers.withings.workouts import WithingsWorkouts


class WithingsStrategy(BaseProviderStrategy):
    """Withings provider implementation.

    Polling-only (no webhook handler) — webhook subscription via Withings
    Notify API can be added in a follow-up phase.
    """

    def __init__(self):
        super().__init__()

        self.oauth = WithingsOAuth(
            user_repo=self.user_repo,
            connection_repo=self.connection_repo,
            provider_name=self.name,
            api_base_url=self.api_base_url,
        )

        self.workouts = WithingsWorkouts(
            workout_repo=self.workout_repo,
            connection_repo=self.connection_repo,
            provider_name=self.name,
            api_base_url=self.api_base_url,
            oauth=self.oauth,
        )

        self.data_247 = Withings247Data(
            provider_name=self.name,
            api_base_url=self.api_base_url,
            oauth=self.oauth,
        )

        self.webhooks = None

    @property
    def name(self) -> str:
        return "withings"

    @property
    def api_base_url(self) -> str:
        # All Withings data calls land on wbsapi.withings.net (form-body POSTs).
        return "https://wbsapi.withings.net"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            rest_pull=True,
            # Withings supports webhooks via the Notify API but we're polling-only
            # for the first phase — fewer surface areas to maintain.
            webhook_ping=False,
        )
