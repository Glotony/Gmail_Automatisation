import base64
import binascii
from email.message import EmailMessage as MIMEEmailMessage
from pathlib import Path

from django.conf import settings

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024

LINK_LABELS = {
    "github_profile": "GitHub პროფილი",
    "public_repositories": "საჯარო რეპოზიტორიები",
}


def get_gmail_service():
    """Authenticate the user and return an authenticated Gmail API client."""
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
            raise FileNotFoundError("credentials.json was not found.")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file),
            settings.GMAIL_SCOPES,
        )
        creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def compose_body(application_message: str, links: dict[str, str]) -> str:
    """Add the separately stored link section to the actual email body."""
    body = application_message.strip()
    visible_links = [(name, url) for name, url in links.items() if url]
    if not visible_links:
        return body

    lines = []
    for name, url in visible_links:
        label = LINK_LABELS.get(name, name.replace("_", " ").strip().capitalize())
        lines.append(f"{label}: {url}")

    return f"{body}\n\nბმულები:\n" + "\n".join(lines)


def send_email(
    recipient: str,
    subject: str,
    body: str,
    attachments: dict[str, dict[str, str]] | None = None,
) -> str:
    """Send an email with optional file attachments through the Gmail API."""
    service = get_gmail_service()
    email = MIMEEmailMessage()
    email["To"] = recipient
    email["Subject"] = subject
    email.set_content(body)

    for section_name, attachment in (attachments or {}).items():
        filename = attachment["filename"]
        mime_type = attachment["mime_type"]
        encoded_content = attachment["content_base64"]

        try:
            content = base64.b64decode(encoded_content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"Attachment {filename!r} contains invalid base64 data.") from exc

        if len(content) > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"Attachment {filename!r} is larger than 15 MiB.")

        if "/" not in mime_type:
            raise ValueError(f"Attachment {filename!r} has an invalid MIME type.")
        maintype, subtype = mime_type.split("/", 1)
        email.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

    encoded_message = base64.urlsafe_b64encode(email.as_bytes()).decode("ascii")
    result = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": encoded_message})
        .execute()
    )
    return result["id"]
