import argparse
import json
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPE = "https://graph.microsoft.com/Mail.Send"
TOKEN_CACHE_FILE = ".token_cache.json"


def load_token_cache() -> SerializableTokenCache:
    cache = SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            cache.deserialize(f.read())
    return cache


def save_token_cache(cache: SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(cache.serialize())


def get_env_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def acquire_token(app: PublicClientApplication, cache: SerializableTokenCache) -> str:
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent([SCOPE], account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=[SCOPE])
    if "user_code" not in flow:
        print("Failed to create device flow.", file=sys.stderr)
        print(flow, file=sys.stderr)
        sys.exit(1)

    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        print("Failed to acquire token.", file=sys.stderr)
        print(result, file=sys.stderr)
        sys.exit(1)

    save_token_cache(cache)
    return result["access_token"]


def send_mail(token: str, sender: str, to_addr: str, subject: str, body: str, is_html: bool) -> None:
    url = f"{GRAPH_BASE}/me/sendMail"
    content_type = "HTML" if is_html else "Text"

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": content_type, "content": body},
            "from": {"emailAddress": {"address": sender}},
            "toRecipients": [{"emailAddress": {"address": to_addr}}],
        },
        "saveToSentItems": True,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    if resp.status_code == 202:
        print("Email sent.")
        return

    print(f"Send failed: {resp.status_code}", file=sys.stderr)
    print(resp.text, file=sys.stderr)
    sys.exit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a test email using Microsoft Graph.")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", default="Test email", help="Email subject")
    parser.add_argument("--body", default="Hello from DevScout-like tool.", help="Email body")
    parser.add_argument("--html", action="store_true", help="Send body as HTML")
    return parser


def main() -> None:
    load_dotenv()

    tenant_id = get_env_value("TENANT_ID")
    client_id = get_env_value("CLIENT_ID")
    sender_email = get_env_value("SENDER_EMAIL")

    cache = load_token_cache()
    app = PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    args = build_arg_parser().parse_args()
    token = acquire_token(app, cache)
    send_mail(token, sender_email, args.to, args.subject, args.body, args.html)


if __name__ == "__main__":
    main()
