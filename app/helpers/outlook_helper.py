import os
import requests
import json
from bs4 import BeautifulSoup
from msal import PublicClientApplication, SerializableTokenCache
import logging
from app import db
from app.models import Request
from datetime import datetime
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load configuration using Config class
config = Config()

# Microsoft Graph API Configuration
CLIENT_ID = config.OUTLOOK_CLIENT_ID
TENANT_ID = config.OUTLOOK_TENANT_ID
CACHE_FILE_PATH = config.OUTLOOK_CACHE_FILE_PATH
SCOPES = config.OUTLOOK_SCOPES

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

class OutlookHelper:
    def __init__(self):
        self.token_cache = self._load_token_cache()
        self.app = PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=self.token_cache
        )

    def _load_token_cache(self):
        """Load token cache from file."""
        token_cache = SerializableTokenCache()
        if os.path.exists(CACHE_FILE_PATH):
            with open(CACHE_FILE_PATH, 'r') as cache_file:
                token_cache.deserialize(cache_file.read())
        return token_cache

    def _save_token_cache(self):
        """Save token cache to file."""
        if self.token_cache.has_state_changed:
            with open(CACHE_FILE_PATH, 'w') as cache_file:
                cache_file.write(self.token_cache.serialize())

    def get_access_token(self):
        """Get a valid access token for Microsoft Graph API."""
        accounts = self.app.get_accounts()
        result = None
        try:
            if accounts:
                result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if not result:
                result = self.app.acquire_token_interactive(scopes=SCOPES)
            self._save_token_cache()
            if result and "access_token" in result:
                logging.info("Access token acquired successfully.")
                return result['access_token']
            else:
                raise Exception(f"Failed to acquire access token. Result: {result}")
        except Exception as e:
            logging.error(f"Error during token acquisition: {e}")
            return None

    def get_filtered_emails(self, access_token):
        """Retrieve unread emails filtered by subject."""
        if not access_token:
            logging.error("No valid access token provided.")
            return []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        url = "https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false and (subject eq 'TV Show Request' or subject eq 'Movie Request' or subject eq 'Music Request')"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('value', [])
        else:
            logging.error(f"Failed to get emails: {response.status_code} - {response.text}")
            return []

    def mark_as_read_and_delete(self, access_token, email_id):
        """Mark an email as read and move it to the 'Deleted Items' folder."""
        if not access_token:
            logging.error("No valid access token provided.")
            return

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Mark the email as read
        mark_read_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
        mark_read_data = {"isRead": True}
        read_response = requests.patch(mark_read_url, headers=headers, json=mark_read_data)
        if read_response.status_code == 200:
            logging.info(f"Marked email {email_id} as read.")
        else:
            logging.error(f"Failed to mark email as read: {read_response.status_code} - {read_response.text}")

        # Move the email to "Deleted Items"
        move_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/move"
        move_data = {"destinationId": "deleteditems"}
        move_response = requests.post(move_url, headers=headers, json=move_data)
        if move_response.status_code == 201:
            logging.info(f"Moved email {email_id} to Deleted Items.")
        else:
            logging.error(f"Failed to move email to Deleted Items: {move_response.status_code} - {move_response.text}")

    def load_processed_message_ids(self):
        """Load processed message IDs from a JSON file."""
        if os.path.exists(CACHE_FILE_PATH):
            try:
                with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    return set(data) if isinstance(data, list) else set()
            except json.JSONDecodeError:
                logging.warning("Processed messages file is corrupted or empty. Resetting to empty.")
                return set()
        return set()

    def save_processed_message_ids(self, message_ids):
        """Save processed message IDs to a JSON file."""
        with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(list(message_ids), file)

    def send_reply_email(self, access_token, email, itemname, category):
        """Send a reply email confirming receipt of a request."""
        if not access_token:
            logging.error("No valid access token provided.")
            return

        reply_body = f"Thank you for your message. The {itemname} has been added to the {category} list."
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        reply_url = f"https://graph.microsoft.com/v1.0/me/messages/{email['id']}/reply"
        data = {
            "message": {
                "body": {
                    "content": reply_body
                }
            }
        }
        response = requests.post(reply_url, headers=headers, json=data)
        if response.status_code == 202:
            logging.info(f"Reply sent for {itemname}")
        else:
            logging.error(f"Failed to send reply email: {response.status_code} - {response.text}")

    def process_requests(self, emails, access_token):
        """Process emails, categorize them, and add to the SQL database."""
        if not emails:
            logging.info("No emails to process.")
            return

        processed_message_ids = self.load_processed_message_ids()

        for email in emails:
            email_id = email.get('id')
            if not email_id or email_id in processed_message_ids:
                continue

            subject = email.get('subject', '').strip()
            body = email.get('body', {}).get('content', '').strip()
            soup = BeautifulSoup(body, 'html.parser')
            title = soup.get_text(separator=" ", strip=True).strip()

            if not title:
                logging.warning(f"No valid title found in the email with ID {email_id}")
                continue

            category = None
            if "tv show request" in subject.lower():
                category = 'TV Show'
            elif "movie request" in subject.lower():
                category = 'Movie'
            elif "music request" in subject.lower():
                category = 'Music'
            else:
                logging.info(f"Unknown request type in subject: {subject}")
                continue

            # Check if the request already exists in the database
            existing_request = Request.query.filter_by(title=title, media_type=category).first()
            if existing_request:
                logging.info(f"{category} '{title}' is already in the database.")
            else:
                # Add the new request to the database
                new_request = Request(
                    user_id=None,  # Specify user ID if known or assign it dynamically
                    media_type=category,
                    title=title,
                    status='Pending',
                    requested_at=datetime.now()
                )
                db.session.add(new_request)
                db.session.commit()
                logging.info(f"Added {category} request: {title}")
                self.send_reply_email(access_token, email, title, category)

            processed_message_ids.add(email_id)
            self.mark_as_read_and_delete(access_token, email_id)

        self.save_processed_message_ids(processed_message_ids)
