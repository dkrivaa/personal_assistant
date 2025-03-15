"""
This file holds the functions for the Google API.
"""

import os.path
import datetime
import base64
import json
from io import BytesIO
from dotenv import load_dotenv, set_key

import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.errors import HttpError


def decode_base64(encoded_str):
    """
    Decodes a Base64-encoded string into a Python dictionary.
    """
    load_dotenv()
    decoded_bytes = base64.b64decode(encoded_str)
    return json.loads(decoded_bytes.decode("utf-8"))


def activate_services():
    """
    Activates Gmail and Google Calendar services.
    """
    load_dotenv()

    # Define scopes for Gmail and Google Calendar
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/calendar'
    ]
    creds = None

    # Decode credentials from environment variables (or Streamlit secrets)
    credentials_json = decode_base64(os.getenv("GOOGLE_CREDENTIALS"))
    token_json = None

    # If a token exists, load it
    if "GOOGLE_TOKEN" in os.environ:
        token_json = decode_base64(os.getenv("GOOGLE_TOKEN"))
        creds = Credentials.from_authorized_user_info(token_json, SCOPES)

    # If no valid credentials, perform authentication
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(credentials_json, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save updated token to .env
        token_b64 = base64.b64encode(creds.to_json().encode()).decode()
        set_key(".env", "GOOGLE_TOKEN", token_b64)

    try:
        # Initialize Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)

        # Initialize Google Calendar service
        calendar_service = build('calendar', 'v3', credentials=creds)

        return gmail_service, calendar_service

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None


######################## GMAIL ##################################


def get_unread_messages(service):
    """Retrieve unread messages."""
    results = service.users().messages().list(userId='me', q="is:unread").execute()
    messages = results.get('messages', [])
    print(messages)

    if not messages:
        print("No unread messages found.")
        return

    for msg in messages:
        msg_id = msg['id']
        msg_details = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        # Extract email details
        headers = msg_details.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print("-" * 50)


def get_recent_messages(service, max_results=5):
    """Retrieve the first N read and unread messages from inbox."""
    results = service.users().messages().list(userId='me', q="in:inbox OR in:Updates",
                                              maxResults=max_results).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
        return

    for msg in messages:
        msg_id = msg['id']
        msg_details = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        # Extract email details
        headers = msg_details.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

        # Check if message is unread
        labels = msg_details.get("labelIds", [])
        status = "Unread" if "UNREAD" in labels else "Read"

        print(f"Status: {status}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print("-" * 50)


def get_attachments(service, msg_id, save_path='./'):
    """Download attachments from an email message."""
    try:
        # Fetch the email message
        msg = service.users().messages().get(userId='me', id=msg_id).execute()

        # Check each part of the message for attachments
        for part in msg['payload']['parts']:
            # If the part contains an attachment
            if 'filename' in part and part['filename']:
                file_name = part['filename']
                mime_type = part['mimeType']
                attachment_id = part['body'].get('attachmentId')

                if attachment_id:
                    # Get the attachment content
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=msg_id, id=attachment_id).execute()

                    # Decode the base64 encoded content
                    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                    # Save the attachment to a file
                    file_path = os.path.join(save_path, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(file_data)

                    print(f"Downloaded attachment: {file_name} of type {mime_type}")

    except HttpError as error:
        print(f"An error occurred: {error}")


def send_email(service, sender, to, subject, body):
    """Send an email using the Gmail API."""
    # Create the email message
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))  # 'plain' for text, 'html' for HTML email

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the email
    message_body = {'raw': raw_message}
    sent_message = service.users().messages().send(userId='me', body=message_body).execute()

    print(f"Email sent! Message ID: {sent_message['id']}")


def send_email_with_attachment(service, sender, to, subject, body, file_path):
    """Send an email with an attachment using the Gmail API."""

    # Create email message
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))  # 'plain' for text, 'html' for HTML email

    # Attach file
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()

    mime_part = MIMEBase('application', 'octet-stream')
    mime_part.set_payload(file_data)
    encoders.encode_base64(mime_part)  # Encode the attachment in base64
    mime_part.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
    message.attach(mime_part)

    # Encode the entire message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send email
    message_body = {'raw': raw_message}
    sent_message = service.users().messages().send(userId='me', body=message_body).execute()

    print(f"Email sent! Message ID: {sent_message['id']}")


def send_email_with_streamlit_attachment(service, sender, to, subject, body, uploaded_file):
    """Send email with an attachment (uploaded via Streamlit) using the Gmail API."""

    # Create the email message
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))  # 'plain' for text, 'html' for HTML email

    # Attach uploaded file
    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_data = uploaded_file.getvalue()  # Get file content as bytes

        mime_part = MIMEBase('application', 'octet-stream')
        mime_part.set_payload(file_data)
        encoders.encode_base64(mime_part)  # Encode attachment in base64
        mime_part.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
        message.attach(mime_part)

    # Encode the entire message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the email
    message_body = {'raw': raw_message}
    sent_message = service.users().messages().send(userId='me', body=message_body).execute()

    st.success(f"✅ Email sent! Message ID: {sent_message['id']}")


def send_email_with_buffers_attachments(service, sender, to, cc, subject, body, file_buffers):
    """
    Send an email with multiple in-memory buffers as attachments using the Gmail API.

    Args:
        service: Authenticated Gmail service instance.
        sender: Email address of the sender.
        to: Email address of the recipient.
        subject: Email subject.
        body: Email body (plain text or HTML).
        file_buffers: List of tuples (file_name, buffer).
                      Example: [("file1.pdf", io.BytesIO(b"data")), ...]
    """

    # Create the email message
    message = MIMEMultipart()
    message['to'] = to
    message['cc'] = cc
    message['from'] = sender
    message['subject'] = subject

    # Attach the body (plain text or HTML)
    message.attach(MIMEText(body, 'plain'))  # Use 'html' if sending HTML content

    # Attach files from buffers
    for file_name, buffer in file_buffers:
        if not isinstance(buffer, BytesIO):
            print(f"Invalid buffer for file: {file_name}")
            continue

        # Move to the start of the buffer
        buffer.seek(0)

        # Create MIME part for the buffer
        mime_part = MIMEBase('application', 'octet-stream')
        mime_part.set_payload(buffer.read())  # Read data from buffer
        encoders.encode_base64(mime_part)  # Encode in base64

        # Add attachment headers
        mime_part.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
        message.attach(mime_part)

    # Encode the entire message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the email
    message_body = {'raw': raw_message}
    sent_message = service.users().messages().send(userId='me', body=message_body).execute()


######################## Calendar ###############################

def get_upcoming_events(service, max_results=5):
    """Retrieve upcoming events sorted by start time."""
    now = datetime.datetime.now(datetime.UTC).isoformat()  # Current time in RFC3339 format
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    if not events:
        print("No upcoming events found.")
        return

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))  # Handle all-day events
        print(f"Event: {event['summary']}")
        print(f"Start Time: {start}")
        print(f'creator: {event['creator']}')
        print(f'organizer: {event['organizer']}')
        print("-" * 50)


