import httpx

from sleeping_beauty.logsys.logger_manager import LoggerManager

LoggerManager.bootstrap()
logger = LoggerManager.get_logger(__name__)


class OuraWebhookAdminClient:
    """
    Client for managing Oura webhook subscriptions.

    Uses app-level authentication:
    - x-client-id
    - x-client-secret
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = "https://api.ouraring.com",
        timeout_s: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_s,
            headers={
                "Accept": "application/json",
                "x-client-id": client_id,
                "x-client-secret": client_secret,
            },
        )

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    async def list_subscriptions(self) -> list[dict]:
        """
        GET /v2/webhook/subscription
        """
        resp = await self._client.get("/v2/webhook/subscription")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # GET (single)
    # ------------------------------------------------------------------

    async def get_subscription(self, subscription_id: str) -> dict:
        """
        GET /v2/webhook/subscription/{id}
        """
        resp = await self._client.get(f"/v2/webhook/subscription/{subscription_id}")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        *,
        callback_url: str,
        data_type: str,
        event_type: str,
        verification_token: str,
    ) -> dict:
        """
        POST /v2/webhook/subscription
        """
        payload = {
            "callback_url": callback_url,
            "verification_token": verification_token,
            "data_type": data_type,
            "event_type": event_type,
        }

        resp = await self._client.post(
            "/v2/webhook/subscription",
            json=payload,
        )

        if resp.status_code >= 400:
            logger.error("Webhook create failed: {}", resp.text)
            resp.raise_for_status()

        return resp.json()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_subscription(
        self,
        *,
        subscription_id: str,
        callback_url: str,
        data_type: str,
        event_type: str,
        verification_token: str,
    ) -> dict:
        """
        PUT /v2/webhook/subscription/{id}
        """
        payload = {
            "callback_url": callback_url,
            "verification_token": verification_token,
            "data_type": data_type,
            "event_type": event_type,
        }

        resp = await self._client.put(
            f"/v2/webhook/subscription/{subscription_id}",
            json=payload,
        )

        if resp.status_code >= 400:
            logger.error("Webhook update failed: {}", resp.text)
            resp.raise_for_status()

        return resp.json()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_subscription(self, subscription_id: str) -> None:
        """
        DELETE /v2/webhook/subscription/{id}

        Oura may return 500 even if deletion succeeds.
        Treat 204, 404, and 500 as non-fatal.
        """
        resp = await self._client.delete(f"/v2/webhook/subscription/{subscription_id}")

        if resp.status_code in (204, 404):
            logger.info(
                "Webhook deleted (or already gone): {}",
                subscription_id,
            )
            return

        if resp.status_code >= 500:
            logger.warning(
                "Webhook delete returned {} for {} — treating as success",
                resp.status_code,
                subscription_id,
            )
            return

        if resp.status_code >= 400:
            logger.error("Webhook delete failed: {}", resp.text)
            resp.raise_for_status()

    # ------------------------------------------------------------------
    # RENEW
    # ------------------------------------------------------------------

    async def renew_subscription(self, subscription_id: str) -> dict:
        """
        PUT /v2/webhook/subscription/renew/{id}
        """
        resp = await self._client.put(
            f"/v2/webhook/subscription/renew/{subscription_id}"
        )

        if resp.status_code >= 400:
            logger.error("Webhook renew failed: {}", resp.text)
            resp.raise_for_status()

        return resp.json()

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.aclose()
