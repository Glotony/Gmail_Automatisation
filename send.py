import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


API_URL = os.getenv(
    "GMAIL_API_URL",
    "http://127.0.0.1:8000/api/email/send/",
)

API_KEY = os.getenv("API_KEY")

INPUT_FILE = BASE_DIR / "sendme.json"


def load_email():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_FILE.name}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    required_fields = {
        "recipient",
        "subject",
        "message",
    }

    missing = required_fields - data.keys()

    if missing:
        raise ValueError(
            "Missing fields: "
            + ", ".join(sorted(missing))
        )

    return data


def send():
    if not API_KEY:
        raise RuntimeError(
            "API_KEY is missing from .env"
        )

    email_data = load_email()

    print("Sending email...")

    response = requests.post(
        API_URL,
        json=email_data,
        headers={
            "X-API-Key": API_KEY,
        },
        timeout=60,
    )

    try:
        result = response.json()
    except ValueError:
        result = {
            "raw_response": response.text
        }

    if not response.ok:
        print("FAILED")
        print(json.dumps(result, indent=4))
        sys.exit(1)

    print("SUCCESS")
    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    send()