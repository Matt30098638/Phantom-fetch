import os
import requests
import time
import json
from bs4 import BeautifulSoup
from msal import PublicClientApplication, SerializableTokenCache

# Microsoft Graph API Configuration
CLIENT_ID = 'c8521d4c-a811-4816-b4de-86d240b8487a'         # Replace with your client ID from Azure
TENANT_ID = '1cb68ff0-8ca0-4b26-a9b9-f49dae9c9b62'         # Replace with your tenant ID from Azure
CACHE_FILE_PATH = 'token_cache.bin'                        # Path to save the token cache
PROCESSED_MESSAGES_FILE = 'processed_messages.json'        # Path to save processed message IDs

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Read", "Mail.Send"]

# Paths to request files
MOVIES_LIST_PATH = 'E:\\requests\\Film-list.txt'
TV_SHOWS_LIST_PATH = 'E:\\requests\\Tv-Shows.txt'
MUSIC_LIST_PATH = 'E:\\requests\\Music-list.txt'

# Initialize MSAL PublicClientApplication with persistent token cache
def load_token_cache():
    token_cache = SerializableTokenCache()
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, 'r') as cache_file:
            cache_data = cache_file.read()
            token_cache.deserialize(cache_data)
    return token_cache

def save_token_cache(token_cache):
    if token_cache.has_state_changed:
        with open(CACHE_FILE_PATH, 'w') as cache_file:
            cache_file.write(token_cache.serialize())

token_cache = load_token_cache()
app = PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    token_cache=token_cache
)

def get_access_token():
    accounts = app.get_accounts()
    result = None
    try:
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            result = app.acquire_token_interactive(scopes=SCOPES)
        save_token_cache(token_cache)
        if result and "access_token" in result:
            return result['access_token']
        else:
            raise Exception(f"Failed to acquire access token. Result: {result}")
    except Exception as e:
        print(f"Error during token acquisition: {e}")
        return None

# Retrieve emails and filter based on the subject line
def get_filtered_emails(access_token):
    if not access_token:
        print("No valid access token provided.")
        return []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = "https://graph.microsoft.com/v1.0/me/messages?$filter=(subject eq 'TV Show Request' or subject eq 'Movie Request' or subject eq 'Music Request')"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('value', [])
    else:
        print(f"Failed to get emails: {response.status_code} - {response.text}")
        return []

# Send a reply email
def send_reply_email(access_token, email, itemname, category):
    if not access_token:
        print("No valid access token provided.")
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
        print(f"Reply sent for {itemname}")
    else:
        print(f"Failed to send reply email: {response.status_code} - {response.text}")

# Process emails and categorize them by content
def process_requests(emails, list_path_movies, list_path_tv, list_path_music, access_token):
    if not emails:
        print("No emails to process.")
        return

    movies_list = []
    tv_shows_list = []
    music_list = []

    if os.path.exists(list_path_movies):
        with open(list_path_movies, 'r', encoding='utf-8') as file:
            movies_list = [line.strip() for line in file.readlines()]

    if os.path.exists(list_path_tv):
        with open(list_path_tv, 'r', encoding='utf-8') as file:
            tv_shows_list = [line.strip() for line in file.readlines()]

    if os.path.exists(list_path_music):
        with open(list_path_music, 'r', encoding='utf-8') as file:
            music_list = [line.strip() for line in file.readlines()]

    processed_message_ids = load_processed_message_ids()

    for email in emails:
        email_id = email.get('id')
        if not email_id or email_id in processed_message_ids:
            continue

        subject = email.get('subject', '').strip()
        body = email.get('body', {}).get('content', '').strip()

        if "TV Show Request" in subject:
            category = 'tv show'
        elif "Movie Request" in subject:
            category = 'movie'
        elif "Music Request" in subject:
            category = 'music'
        else:
            continue  # Skip unrecognized requests

        soup = BeautifulSoup(body, 'html.parser')
        title = soup.get_text(strip=True).strip()

        title_lower = title.lower()
        if category == 'movie':
            if title_lower not in [m.lower() for m in movies_list]:
                movies_list.append(title)
                movies_list.sort()
                with open(list_path_movies, 'w', encoding='utf-8') as file:
                    file.write("\n".join(movies_list) + "\n")
                print(f"Added movie request: {title}")
                send_reply_email(access_token, email, title, "movie")
        elif category == 'tv show':
            if title_lower not in [t.lower() for t in tv_shows_list]:
                tv_shows_list.append(title)
                tv_shows_list.sort()
                with open(list_path_tv, 'w', encoding='utf-8') as file:
                    file.write("\n".join(tv_shows_list) + "\n")
                print(f"Added TV show request: {title}")
                send_reply_email(access_token, email, title, "tv show")
        elif category == 'music':
            if title_lower not in [m.lower() for m in music_list]:
                music_list.append(title)
                music_list.sort()
                with open(list_path_music, 'w', encoding='utf-8') as file:
                    file.write("\n".join(music_list) + "\n")
                print(f"Added music request: {title}")
                send_reply_email(access_token, email, title, "music")

        processed_message_ids.add(email_id)

    save_processed_message_ids(processed_message_ids)

# Main function to continuously monitor emails for requests
if __name__ == "__main__":
    print("Starting continuous monitoring for email requests...")

    while True:
        try:
            access_token = get_access_token()
            if not access_token:
                raise Exception("No valid access token was obtained.")

            emails = get_filtered_emails(access_token)
            process_requests(emails, 
                             MOVIES_LIST_PATH, 
                             TV_SHOWS_LIST_PATH, 
                             MUSIC_LIST_PATH,
                             access_token)

            print("Sleeping for 5 minutes before the next check...")
            time.sleep(300)

        except Exception as e:
            print(f"An error occurred: {e}. Retrying in 60 seconds...")
            time.sleep(60)
