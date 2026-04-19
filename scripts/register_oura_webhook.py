#!/usr/bin/env python3
"""
One-shot Oura webhook provisioning script.

Behavior (INTENTIONAL):
- Lists all existing webhook subscriptions
- Deletes ALL of them (with explicit output)
- Re-creates subscriptions declared in WEBHOOK_SUBSCRIPTIONS

This is a destructive reset tool.
Run only when you intend to re-provision webhooks.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pprint import pprint

import httpx

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.clients.oura_webhook_admin import OuraWebhookAdminClient
from sleeping_beauty.config.config import Config
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.oura_auth import OuraAuth

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

WEBHOOK_URL = "https://oura.hicsvntdracons.xyz/oura/webhook"

# WEBHOOK_SUBSCRIPTIONS = [
#     # Strong, reliable signals
#     {"data_type": "workout", "event_type": "create"},
#     {"data_type": "workout", "event_type": "update"},
#     {"data_type": "workout", "event_type": "delete"},
#     {"data_type": "sleep", "event_type": "create"},
#     # Optional / weaker signals
#     # {"data_type": "tag", "event_type": "create"},
#     # {"data_type": "daily_readiness", "event_type": "update"},
# ]

## event_type: Enum: "create" "update" "delete"
## data_type: Enum: (
#     "tag"
#     "enhanced_tag"
#     "workout"
#     "session"
#     "sleep"
#     "daily_sleep"
#     "daily_readiness"
#     "daily_activity"
#     "daily_spo2"
#     "sleep_time"
#     "rest_mode_period"
#     "ring_configuration"
#     "daily_stress"
#     "daily_cardiovascular_age"
#     "daily_resilience"
#     "vo2_max"
# )

WEBHOOK_SUBSCRIPTIONS = [
    # ------------------------------------------------------------------
    # TAGS
    # ------------------------------------------------------------------
    {"data_type": "tag", "event_type": "create"},
    {"data_type": "tag", "event_type": "update"},
    {"data_type": "tag", "event_type": "delete"},
    {"data_type": "enhanced_tag", "event_type": "create"},
    {"data_type": "enhanced_tag", "event_type": "update"},
    {"data_type": "enhanced_tag", "event_type": "delete"},
    # ------------------------------------------------------------------
    # WORKOUT / SESSION
    # ------------------------------------------------------------------
    {"data_type": "workout", "event_type": "create"},
    {"data_type": "workout", "event_type": "update"},
    {"data_type": "workout", "event_type": "delete"},
    {"data_type": "session", "event_type": "create"},
    {"data_type": "session", "event_type": "update"},
    {"data_type": "session", "event_type": "delete"},
    # ------------------------------------------------------------------
    # SLEEP
    # ------------------------------------------------------------------
    {"data_type": "sleep", "event_type": "create"},
    {"data_type": "sleep", "event_type": "update"},
    {"data_type": "sleep", "event_type": "delete"},
    {"data_type": "daily_sleep", "event_type": "create"},
    {"data_type": "daily_sleep", "event_type": "update"},
    {"data_type": "daily_sleep", "event_type": "delete"},
    {"data_type": "sleep_time", "event_type": "create"},
    {"data_type": "sleep_time", "event_type": "update"},
    {"data_type": "sleep_time", "event_type": "delete"},
    # ------------------------------------------------------------------
    # READINESS / ACTIVITY / PHYSIOLOGY
    # ------------------------------------------------------------------
    {"data_type": "daily_readiness", "event_type": "create"},
    {"data_type": "daily_readiness", "event_type": "update"},
    {"data_type": "daily_readiness", "event_type": "delete"},
    {"data_type": "daily_activity", "event_type": "create"},
    {"data_type": "daily_activity", "event_type": "update"},
    {"data_type": "daily_activity", "event_type": "delete"},
    {"data_type": "daily_spo2", "event_type": "create"},
    {"data_type": "daily_spo2", "event_type": "update"},
    {"data_type": "daily_spo2", "event_type": "delete"},
    {"data_type": "daily_stress", "event_type": "create"},
    {"data_type": "daily_stress", "event_type": "update"},
    {"data_type": "daily_stress", "event_type": "delete"},
    # ------------------------------------------------------------------
    # CARDIO / RESILIENCE
    # ------------------------------------------------------------------
    {"data_type": "daily_cardiovascular_age", "event_type": "create"},
    {"data_type": "daily_cardiovascular_age", "event_type": "update"},
    {"data_type": "daily_cardiovascular_age", "event_type": "delete"},
    {"data_type": "daily_resilience", "event_type": "create"},
    {"data_type": "daily_resilience", "event_type": "update"},
    {"data_type": "daily_resilience", "event_type": "delete"},
    {"data_type": "vo2_max", "event_type": "create"},
    {"data_type": "vo2_max", "event_type": "update"},
    {"data_type": "vo2_max", "event_type": "delete"},
    # ------------------------------------------------------------------
    # DEVICE / STATE
    # ------------------------------------------------------------------
    {"data_type": "rest_mode_period", "event_type": "create"},
    {"data_type": "rest_mode_period", "event_type": "update"},
    {"data_type": "rest_mode_period", "event_type": "delete"},
    {"data_type": "ring_configuration", "event_type": "create"},
    {"data_type": "ring_configuration", "event_type": "update"},
    {"data_type": "ring_configuration", "event_type": "delete"},
]


def parse_args():
    parser = argparse.ArgumentParser(description="Oura webhook provisioning tool")
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List existing webhook subscriptions and exit",
    )
    parser.add_argument(
        "--whoami",
        action="store_true",
        help="Fetch personal info for the currently authorized Oura user and exit",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


async def main(args) -> None:
    # --------------------------------------------------------------
    # Load config
    # --------------------------------------------------------------
    config = Config()
    config.load_from_yaml("configs/config.yaml")

    verification_token = config.oura_webhook_verification_token
    if not verification_token:
        raise RuntimeError("oura_webhook_verification_token is not set")

    # --------------------------------------------------------------
    # Create admin client
    # --------------------------------------------------------------
    admin = OuraWebhookAdminClient(
        client_id=config.oura_client_id,
        client_secret=config.oura_client_secret,
    )

    try:

        if args.whoami:
            await print_oura_identity()
            return

        # ----------------------------------------------------------
        # List existing subscriptions
        # ----------------------------------------------------------
        hooks = await admin.list_subscriptions()

        if hooks:
            print("\nExisting webhook subscriptions (will be deleted):")
            for h in hooks:
                print(
                    f"- id={h.get('id')} "
                    f"url={h.get('callback_url')} "
                    f"data_type={h.get('data_type')} "
                    f"event_type={h.get('event_type')} "
                    f"exp={h.get('expiration_time')}"
                )
        else:
            print("\nNo existing webhook subscriptions found.")

        # ----------------------------------------------------------
        # List-only mode: exit early
        # ----------------------------------------------------------
        if args.list_only:
            print("\n--list-only specified; exiting without changes.")
            return

        # ----------------------------------------------------------
        # Delete all existing subscriptions
        # ----------------------------------------------------------
        for h in hooks:
            sub_id = h.get("id")
            if not sub_id:
                continue

            print(f"Deleting webhook subscription: {sub_id}")
            await admin.delete_subscription(sub_id)

        if hooks:
            print("All existing webhook subscriptions deleted.\n")

        # ----------------------------------------------------------
        # Re-create desired subscriptions
        # ----------------------------------------------------------
        print("Re-creating declared webhook subscriptions:")

        for sub in WEBHOOK_SUBSCRIPTIONS:
            print(f"- Creating {sub['data_type']}/{sub['event_type']} → {WEBHOOK_URL}")

            try:
                created = await admin.create_subscription(
                    callback_url=WEBHOOK_URL,
                    verification_token=verification_token,
                    data_type=sub["data_type"],
                    event_type=sub["event_type"],
                )
            except httpx.RequestError as exc:
                print("  Failed:")
                print(f"    transport_error: {exc}")
                continue

            if not created:
                print("  Failed:")
                print(f"    status_code: {created.status_code}")
                print(f"    error: {created.error}")
                continue

            result = created.result or {}

            print("  Created:")
            print(f"    id: {result.get('id')}")
            print(f"    expires: {result.get('expiration_time')}")

        print("\nWebhook provisioning complete.")

    finally:
        await admin.aclose()


async def print_oura_identity() -> None:
    """
    Fetch and print the currently authorized Oura user identity.

    Uses the standard OuraAuth preflight + token provider flow.
    """

    oura_auth = OuraAuth.from_config()
    preflight: AuthPreflightReport = oura_auth.preflight_check()

    if not preflight.ok:
        print("\n".join(preflight.messages))
        # raise RuntimeError("Oura authentication preflight failed")

    client = OuraApiClient(token_provider=oura_auth.get_access_token)

    try:
        info = await client.get_personal_info()

        print("\nOura identity:")
        print(f"  user_id: {info.user_id}")

        if hasattr(info, "email"):
            print(f"  email: {info.email}")

        if hasattr(info, "timezone"):
            print(f"  timezone: {info.timezone}")
        else:
            now = datetime.now().astimezone()
            tz_name = str(now.tzinfo)

            offset = now.utcoffset()
            total_minutes = int(offset.total_seconds() // 60)
            hours, minutes = divmod(abs(total_minutes), 60)
            sign = "+" if total_minutes >= 0 else "-"
            offset_str = f"UTC{sign}{hours:02d}:{minutes:02d}"

            print(f"  timezone: {tz_name} ({offset_str})")

    finally:
        await client.aclose()


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    try:
        args = parse_args()
        asyncio.run(main(args))
    except KeyboardInterrupt:
        sys.exit(130)
