import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from sleeping_beauty.clients.oura_webhook_admin import OuraWebhookAdminClient
from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.oura.auth.oura_auth import OuraAuth

logger = LoggerManager.get_logger(__name__)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sleeping_beauty.ingress")

config = Config()
config.config_path = "configs/config.yaml"
config.load_from_yaml(config.config_path)


WEBHOOK_URL = "https://oura.hicsvntdracons.xyz/oura/webhook"

# -------------------------------------------------
# Authentication preflight (IDENTICAL to summary)
# -------------------------------------------------
oura_auth = OuraAuth.from_config()


def verify_oura_signature(raw_body: bytes, signature: str) -> bool:
    """
    Verify Oura webhook signature using HMAC-SHA256.

    Signature is expected to be uppercase hex.
    """
    logging.info("verifying signature")
    secret = config.oura_webhook_secret.encode("utf-8")

    if not secret:
        return False

    computed = (
        hmac.new(
            key=secret,
            msg=raw_body,
            digestmod=hashlib.sha256,
        )
        .hexdigest()
        .upper()
    )

    return hmac.compare_digest(computed, signature)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Sleeping Beauty ingress starting up")

    # IMPORTANT:
    # - no webhook registration here
    # - no network calls
    # - ingress must start instantly

    yield

    # SHUTDOWN
    logger.info("Sleeping Beauty ingress shutting down")


app = FastAPI(
    title="Sleeping Beauty – Oura Ingress",
    version="0.0.1",
    lifespan=lifespan,
)


@app.get("/oura/webhook")
@app.get("/oura/webhook/")
async def oura_webhook_challenge(request: Request):
    params = request.query_params

    challenge = params.get("challenge")
    verification_token = params.get("verification_token")

    if challenge:
        # -------------------------------------------------
        # Verify token matches what we registered with Oura
        # -------------------------------------------------
        expected = config.oura_webhook_verification_token

        if not expected:
            logger.error("Webhook verification token not configured")
            raise HTTPException(status_code=500)

        if verification_token != expected:
            logger.warning(
                "Invalid webhook verification token: {}",
                verification_token,
            )
            raise HTTPException(status_code=401)

        logger.info("Responding to verified Oura webhook challenge")

        return JSONResponse(
            status_code=200,
            content={"challenge": challenge},
        )

    # -------------------------------------------------
    # Optional: health probe (non-Oura)
    # -------------------------------------------------
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.post("/oura/webhook", status_code=204)
@app.post("/oura/webhook/", status_code=204)
async def oura_webhook(request: Request):

    logger.info("Processing webhook event")
    raw_body = await request.body()

    logger.info(
        "Headers=%s BodyBytes=%d",
        dict(request.headers),
        len(raw_body),
    )

    # -------------------------------------------------
    # Oura webhook verification challenge
    # -------------------------------------------------
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload = None

    if isinstance(payload, dict) and "challenge" in payload:
        logger.info(
            f"Responding to Oura webhook verification challenge: {payload.get("challenge")}"
        )
        return JSONResponse(
            status_code=200,
            content={"challenge": payload["challenge"]},
        )

    # -------------------------------------------------
    # Normal webhook delivery (signed)
    # -------------------------------------------------
    signature = request.headers.get("x-oura-signature")
    if not signature:
        raise HTTPException(status_code=401)

    if not verify_oura_signature(raw_body, signature):
        raise HTTPException(status_code=401)

    logger.info(
        "Verified Oura webhook: bytes=%d content_type=%s",
        len(raw_body),
        request.headers.get("content-type"),
    )

    return
