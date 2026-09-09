import base64
from email.message import EmailMessage
from pathlib import Path

from django.conf import settings

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def get_gmail_service():
    """
    Authenticate the user and return an authenticated Gmail API client.
    """

    creds = None

    token_file = Path(settings.GMAIL_TOKEN_FILE)
    credentials_file = Path(settings.GMAIL_CREDENTIALS_FILE)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_file),
            settings.GMAIL_SCOPES,
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    elif not creds or not creds.valid:
        if not credentials_file.exists():
            raise FileNotFoundError(
                "credentials.json was not found."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file),
            settings.GMAIL_SCOPES,
        )

        creds = flow.run_local_server(
            port=0
        )

        token_file.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

    return build(
        "gmail",
        "v1",
        credentials=creds,
    )


def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> str:
    """
    Send one email through Gmail.

    Returns:
        Gmail message ID.
    """

    service = get_gmail_service()

    email = EmailMessage()

    email["To"] = recipient
    email["Subject"] = subject

    email.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode()

    request_body = {
        "raw": encoded_message,
    }

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body=request_body,
        )
        .execute()
    )

    return result["id"]