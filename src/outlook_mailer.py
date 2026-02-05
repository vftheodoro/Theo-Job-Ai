import argparse
import json
import os
import re
import sys
from typing import Optional, Tuple

import google.generativeai as genai
from dotenv import load_dotenv
from msal import PublicClientApplication

import send_mail as base_mail


def configure_gemini(api_key: str) -> None:
    if not api_key:
        print("GEMINI_API_KEY is required when using --brief", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)


def parse_json_like(text: str) -> Optional[dict]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def generate_email(api_key: str, brief: str, sender_name: str) -> Tuple[str, str]:
    configure_gemini(api_key)
    prompt = (
        "You draft concise outreach emails. Return JSON with keys 'subject' and 'body'. "
        "Subject <= 70 chars. Body <= 120 words. Tone: professional, warm. "
        f"Sender name: {sender_name or 'Sender'}. Brief/context: {brief}."
    )
    response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
    text = response.text or ""
    parsed = parse_json_like(text)
    if parsed and "subject" in parsed and "body" in parsed:
        return parsed["subject"].strip(), parsed["body"].strip()
    # Fallback: use whole text as body with default subject
    return "Follow-up", text.strip() or "Hello, this is a generated email body."


def build_app(tenant_id: str, client_id: str, cache) -> PublicClientApplication:
    return PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )


def main() -> None:
    load_dotenv()

    tenant_id = base_mail.get_env_value("TENANT_ID")
    client_id = base_mail.get_env_value("CLIENT_ID")
    default_sender = base_mail.get_env_value("SENDER_EMAIL")
    gemini_key = os.getenv("GEMINI_API_KEY")

    parser = argparse.ArgumentParser(description="Send an email via Outlook (Graph) with optional Gemini drafting.")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", help="Email subject (overridden if --brief is used)")
    parser.add_argument("--body", help="Email body text (overridden if --brief is used)")
    parser.add_argument("--html", action="store_true", help="Send body as HTML")
    parser.add_argument("--brief", help="If set, use Gemini to generate subject/body from this context")
    parser.add_argument("--from-email", dest="from_email", default=default_sender, help="Sender email to use (defaults to env SENDER_EMAIL)")
    parser.add_argument("--sender-name", dest="sender_name", default="", help="Sender display name for Gemini prompt")
    args = parser.parse_args()

    sender_email = (args.from_email or "").strip()
    if not sender_email:
        print("Sender email is required (env SENDER_EMAIL or --from-email)", file=sys.stderr)
        sys.exit(1)

    subject = args.subject
    body = args.body

    if args.brief:
        subject, body = generate_email(gemini_key or base_mail.get_env_value("GEMINI_API_KEY"), args.brief, args.sender_name)

    subject = subject or "Test email"
    body = body or "Hello from Outlook mailer."

    cache = base_mail.load_token_cache()
    app = build_app(tenant_id, client_id, cache)
    token = base_mail.acquire_token(app, cache)
    base_mail.send_mail(token, sender_email, args.to, subject, body, args.html)


if __name__ == "__main__":
    main()
