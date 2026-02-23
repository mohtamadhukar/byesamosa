"""IMAP-based OTP retrieval for Oura login.

Connects to a dedicated Gmail account (proxy) via IMAP with an app password.
Oura OTP emails are forwarded from the main account to this proxy.
"""

import email
import email.message
import email.utils
import imaplib
import re
import time
from datetime import datetime, timezone

from byesamosa.config import Settings

OURA_SENDER = "support@ouraring.com"


def fetch_oura_otp(sent_after: float | None = None, timeout_seconds: int = 120) -> str:
    """Poll the proxy Gmail inbox for a recent Oura OTP email and extract the code.

    Args:
        sent_after: Unix timestamp — only consider emails received after this time.
                    If None, uses (now - 60 seconds).
        timeout_seconds: How long to poll before giving up.

    Returns:
        The OTP code string (typically 6 digits).

    Raises:
        TimeoutError: If no OTP email is found within the timeout.
    """
    settings = Settings()

    if not settings.gmail_otp_email or not settings.gmail_otp_app_password:
        raise ValueError(
            "GMAIL_OTP_EMAIL and GMAIL_OTP_APP_PASSWORD must be set in .env\n"
            "See docs/PLAN_PULL_COMMAND.md for setup instructions."
        )

    if sent_after is None:
        sent_after = time.time() - 60
    # No tolerance — only accept emails strictly after the cutoff.
    # The new OTP email will have a timestamp after sent_after.

    print("Waiting for Oura OTP email...")
    start = time.time()

    while time.time() - start < timeout_seconds:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(settings.gmail_otp_email, settings.gmail_otp_app_password)
            mail.select("inbox")

            # Search for Oura emails
            _, msg_nums = mail.search(None, '(FROM "ouraring.com")')
            msg_ids = msg_nums[0].split()

            for msg_id in reversed(msg_ids):  # newest first
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Check email date — skip old emails
                date_str = msg.get("Date", "")
                try:
                    msg_date = email.utils.parsedate_to_datetime(date_str)
                    msg_timestamp = msg_date.timestamp()
                except Exception:
                    msg_timestamp = time.time()

                if msg_timestamp < sent_after:
                    continue

                otp = _extract_otp(msg)
                if otp:
                    print(f"OTP retrieved: {otp}")
                    mail.logout()
                    return otp

            mail.logout()
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")

        time.sleep(5)

    raise TimeoutError(
        f"No Oura OTP email found within {timeout_seconds} seconds. "
        "Check that email forwarding is working and the OTP email arrived."
    )


def _extract_otp(msg: email.message.Message) -> str | None:
    """Extract 6-digit OTP code from an email message."""
    body = _get_body_text(msg)
    if not body:
        return None

    match = re.search(r"\b(\d{6})\b", body)
    return match.group(1) if match else None


def _get_body_text(msg: email.message.Message) -> str | None:
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")

    return None
