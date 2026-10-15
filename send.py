"""Load a nested sendme.json, prepare attachments, and call the Django API."""

import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("GMAIL_API_URL", "http://127.0.0.1:8000/api/email/send/")
API_KEY = os.getenv("API_KEY")
INPUT_FILE = BASE_DIR / "sendme.json"

# Gmail's total message size limit is 25 MB. Keep attachment data well under it
# because base64 encoding increases the payload size by roughly one third.
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 18 * 1024 * 1024

MIME_FALLBACKS = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


def normalize_document(document: Any) -> dict[str, Any]:
    """Accept a nested object or an array of nested section objects.

    Preferred object form:
      {"recipient": "...", "subject": {"text": "..."}, ...}

    Also accepts the user's section-array form:
      [{"recipient": "..."}, {"subject": {"text": "..."}}, ...]

    The old flat {recipient, subject, message} form is intentionally rejected.
    """
    if isinstance(document, list):
        merged: dict[str, Any] = {}
        for index, section in enumerate(document):
            if not isinstance(section, dict):
                raise ValueError(
                    f"Section #{index + 1} must be a JSON object."
                )
            if len(section) != 1:
                raise ValueError(
                    f"Section #{index + 1} must contain exactly one top-level key."
                )
            key = next(iter(section))
            if key in merged:
                raise ValueError(f"Duplicate section: {key!r}.")
            merged[key] = section[key]
        document = merged

    if not isinstance(document, dict):
        raise ValueError(
            "sendme.json must contain a nested JSON object or an array of nested section objects."
        )

    allowed_keys = {"recipient", "subject", "application", "files", "links"}
    unknown_keys = set(document) - allowed_keys
    if unknown_keys:
        raise ValueError(
            "Unknown top-level section(s): " + ", ".join(sorted(unknown_keys))
        )

    if not isinstance(document.get("subject"), dict):
        raise ValueError('Use a nested subject section: "subject": {"text": "..."}.')
    if not isinstance(document.get("application"), dict):
        raise ValueError(
            'Use a nested application section: "application": {"message": "..."}.'
        )

    return document


def _attachment_config(name: str, value: Any) -> tuple[Path, str | None, str | None]:
    """Read a source attachment entry, which may be a path or a config object."""
    if isinstance(value, str):
        raw_path, filename, mime_type = value, None, None
    elif isinstance(value, dict):
        raw_path = value.get("path")
        filename = value.get("filename")
        mime_type = value.get("mime_type")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f'files.{name} must include a non-empty "path".')
    else:
        raise ValueError(
            f"files.{name} must be a file path string or an object containing path/filename/mime_type."
        )

    path = Path(raw_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(
            f"Attachment for files.{name} was not found: {path}"
        )

    safe_filename = filename or path.name
    if not isinstance(safe_filename, str) or not safe_filename.strip():
        raise ValueError(f"files.{name} has an invalid filename.")
    if Path(safe_filename).name != safe_filename or any(ch in safe_filename for ch in ("/", "\\", "\r", "\n")):
        raise ValueError(f"Attachment filename must not contain a path: {safe_filename!r}")

    if mime_type is not None and (not isinstance(mime_type, str) or "/" not in mime_type):
        raise ValueError(f"files.{name} has an invalid mime_type.")

    if not mime_type:
        mime_type = mimetypes.guess_type(safe_filename)[0]
        if not mime_type:
            mime_type = MIME_FALLBACKS.get(Path(safe_filename).suffix.lower(), "application/octet-stream")

    return path, safe_filename, mime_type


def prepare_attachments(files: Any) -> dict[str, dict[str, str]]:
    """Read local files and return JSON-safe attachment payloads."""
    if files is None:
        return {}
    if not isinstance(files, dict):
        raise ValueError('"files" must be a nested object, for example {"cv": "C:\\\\path\\\\cv.docx"}.')

    prepared: dict[str, dict[str, str]] = {}
    total_size = 0

    for key, value in files.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Each files entry must have a non-empty name, such as 'cv'.")

        path, filename, mime_type = _attachment_config(key, value)
        size = path.stat().st_size
        if size > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment {filename!r} is larger than 15 MiB. Choose a smaller file."
            )
        total_size += size
        if total_size > MAX_TOTAL_ATTACHMENT_BYTES:
            raise ValueError("Combined attachments exceed 18 MiB. Choose smaller files.")

        content_base64 = base64.b64encode(path.read_bytes()).decode("ascii")
        prepared[key] = {
            "filename": filename,
            "mime_type": mime_type,
            "content_base64": content_base64,
        }

    return prepared


def load_email() -> dict[str, Any]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing {INPUT_FILE.name}")

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        raw_document = json.load(file)

    data = normalize_document(raw_document)

    recipient = data.get("recipient")
    if not isinstance(recipient, str) or not recipient.strip() or recipient.strip() == "*":
        raise ValueError('Replace "recipient": "*" with the real recipient email address before sending.')
    if "@" not in recipient or any(char.isspace() for char in recipient):
        raise ValueError(f"Recipient does not look like an email address: {recipient!r}")

    subject = data["subject"].get("text")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError('The nested section "subject.text" must be a non-empty string.')

    application = data["application"].get("message")
    if not isinstance(application, str) or not application.strip():
        raise ValueError('The nested section "application.message" must be a non-empty string.')

    links = data.get("links", {})
    if not isinstance(links, dict):
        raise ValueError('"links" must be a nested object.')
    for name, url in links.items():
        if not isinstance(name, str) or not isinstance(url, str):
            raise ValueError("Each links entry must map a name to a URL string.")
        if url and not url.startswith(("https://", "http://")):
            raise ValueError(f"Link {name!r} must start with http:// or https://.")

    # Keep the nested structure; only replace local paths with encoded contents
    # for the API request. The original sendme.json remains unchanged.
    data["files"] = prepare_attachments(data.get("files", {}))
    data.setdefault("links", {})
    return data


def send() -> None:
    if not API_KEY:
        raise RuntimeError("API_KEY is missing from .env")

    email_data = load_email()
    print("Sending email...")

    response = requests.post(
        API_URL,
        json=email_data,
        headers={"X-API-Key": API_KEY},
        timeout=60,
    )

    try:
        result = response.json()
    except ValueError:
        result = {"raw_response": response.text}

    if not response.ok:
        print("FAILED")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        sys.exit(1)

    print("SUCCESS")
    print(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    try:
        send()
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
