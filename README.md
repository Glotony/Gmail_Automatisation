HOW TO START

You will need 2 PowerShell tabs.

========================
TAB 1 — START THE SERVER
========================

cd path\to\gmail_automation

Run:

python manage.py runserver

Leave this tab running.

========================
TAB 2 — SEND THE EMAIL
========================

cd path\to\gmail_automation

Run:

python send.py

This will send everything written in sendme.json.

========================
EDIT THE EMAIL
==============

Before running send.py, accurately change:

recipient
subject
message

inside sendme.json.

Example:

{
  "recipient": "example@gmail.com",
  "subject": "Hello",
  "message": "Hello from my automation API!"
}

========================
GOOGLE AUTHORIZATION
====================

This project uses the Gmail API with Google OAuth 2.0.

Google Cloud was configured with:

* Google Cloud project
* Gmail API enabled
* OAuth configuration
* OAuth application in testing mode
* Sender Google account added as a test user
* OAuth client created as a Desktop application

The downloaded Google OAuth client file is:

credentials.json

Place it directly inside the project folder.

The Gmail permission requested by this project is:

https://www.googleapis.com/auth/gmail.send

========================
SENDER VS RECIPIENT
===================

The Google account selected during OAuth is the account that
SENDS the email.

The "recipient" inside sendme.json is the account that
RECEIVES the email.

Example:

Google OAuth account
|
| SEND
v
recipient from sendme.json

========================
GOOGLE OAUTH TOKEN
==================

The first time:

python send.py

is executed, Google opens the OAuth authorization page.

Choose the Google account that will send the email and authorize
the application.

After successful authorization, the application saves the OAuth
authorization locally as:

token.json

This token allows the application to reuse the Google authorization
on future runs instead of asking the user to authorize again every
time.

If token.json is deleted, the application will need to authorize
the Google account again.

DO NOT upload token.json to GitHub.

========================
DJANGO SECRET KEY
=================

DJANGO_SECRET_KEY is the secret used by Django.

It was generated locally with:

python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

The generated value was then placed in:

.env

Example:

DJANGO_SECRET_KEY="generated-secret-here"

This value is NOT obtained from Google.

It is generated locally for the Django project.

DO NOT publish or commit it.

========================
PRIVATE API KEY
===============

The Django API is protected with a private API key.

The API key was generated locally with:

python -c "import secrets; print(secrets.token_urlsafe(32))"

The generated value was then placed in:

.env

Example:

API_KEY="generated-private-api-key-here"

This API key is NOT provided by Google.

It was generated specifically for this Django API.

send.py reads the API key from .env and sends it to Django using:

X-API-Key

The Django backend compares the received API key with the API key
stored in its environment.

DO NOT publish or commit the API key.

========================
IMPORTANT PRIVATE FILES
=======================

The following files contain secrets or local/private data:

.env
credentials.json
token.json
db.sqlite3

These files should NOT be uploaded to GitHub.

The .gitignore file should contain:

.env
credentials.json
token.json
db.sqlite3

========================
NORMAL USAGE
============

1. Start Django:

python manage.py runserver

2. Edit sendme.json.

3. Run:

python send.py

The contents of sendme.json are sent through the Django API and
then through the Gmail API.

After Google OAuth has been completed once, future sends normally
use the saved token.json authorization.

========================
CORE WORKFLOW
=============

sendme.json
|
v
send.py
|
| X-API-Key
v
Django API
|
v
Gmail API
|
v
SENT EMAIL
