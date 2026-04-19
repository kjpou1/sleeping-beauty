#!/usr/bin/env python3

import argparse
import asyncio
import sys
from datetime import datetime

import httpx

from sleeping_beauty.clients.oura_api_client import OuraApiClient
from sleeping_beauty.clients.oura_webhook_admin import OuraWebhookAdminClient
from sleeping_beauty.config.config import Config
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.oura_auth import OuraAuth

WEBHOOK_CATCHER_URL = "https://catcher.hicsvntdracons.xyz/oura/webhook"

WEBHOOK_SUBSCRIPTION = {
    "data_type": "daily_sleep",
    "event_type": "create",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Register a single Oura catcher webhook"
    )
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


async def print_oura_identity() -> None:
    oura_auth = OuraAuth.from_config()
    preflight: AuthPreflightReport = oura_auth.preflight_check()

    if not preflight.ok:
        print("\n".join(preflight.messages))
        raise RuntimeError("Oura authentication preflight failed")

    client = OuraApiClient(token_provider=oura_auth.get_access_token)

    try:
        info = await client.get_personal_info()

        print("\nOura identity:")
        print(f"  user_id: {info.user_id}")
        print(f"  email: {info.email}")

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


async def main(args) -> None:
    config = Config()
    config.load_from_yaml("configs/config.yaml")

    if args.whoami:
        await print_oura_identity()
        return

    verification_token = config.oura_webhook_verification_token
    if not verification_token:
        raise RuntimeError("oura_webhook_verification_token is not set")

    admin = OuraWebhookAdminClient(
        client_id=config.oura_client_id,
        client_secret=config.oura_client_secret,
    )

    try:
        hooks = await admin.list_subscriptions()

        if hooks:
            print("\nExisting webhook subscriptions:")
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

        print(
            f"\nCreating catcher subscription: "
            f"{WEBHOOK_SUBSCRIPTION['data_type']}/{WEBHOOK_SUBSCRIPTION['event_type']} "
            f"→ {WEBHOOK_CATCHER_URL}"
        )

        try:
            created = await admin.create_subscription(
                callback_url=WEBHOOK_CATCHER_URL,
                verification_token=verification_token,
                data_type=WEBHOOK_SUBSCRIPTION["data_type"],
                event_type=WEBHOOK_SUBSCRIPTION["event_type"],
            )
        except httpx.RequestError as exc:
            print("  Failed:")
            print(f"    transport_error: {exc}")
            return

        if not created:
            print("  Failed:")
            print(f"    status_code: {created.status_code}")
            print(f"    error: {created.error}")
            return

        result = created.result or {}

        print("  Created:")
        print(f"    id: {result.get('id')}")
        print(f"    callback_url: {result.get('callback_url')}")
        print(f"    data_type: {result.get('data_type')}")
        print(f"    event_type: {result.get('event_type')}")
        print(f"    expires: {result.get('expiration_time')}")

    finally:
        await admin.aclose()


if __name__ == "__main__":
    try:
        args = parse_args()
        asyncio.run(main(args))
    except KeyboardInterrupt:
        sys.exit(130)
