import os
import subprocess
import sys
import yaml
import webbrowser
import platform
import urllib.request
import zipfile
from msal import PublicClientApplication
from spotipy.oauth2 import SpotifyOAuth

# Constants
INSTALL_PATH = "C:\\Torrenter"
ASSETS_PATH = os.path.join(INSTALL_PATH, "assets")
CONFIG_FILE_PATH = os.path.join(ASSETS_PATH, 'config.yaml')
DEPENDENCIES = ["requests", "qbittorrent-api", "msal", "beautifulsoup4", "pyyaml", "spotipy", "pyinstaller"]

# Microsoft Graph-related Constants
GRAPH_AUTHORITY = "https://login.microsoftonline.com/"
GRAPH_SCOPE = ["Mail.Read", "Mail.Send"]
MICROSOFT_REDIRECT_URI = "http://localhost:8000"  # Needs to be added in Azure app registration

# Spotify-related Constants
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# URLs for downloading tools and project
JACKETT_WINDOWS_URL = "https://github.com/Jackett/Jackett/releases/latest/download/Jackett.Binaries.Windows.zip"
QBITTORRENT_WINDOWS_URL = "https://www.fosshub.com/qBittorrent.html"
PHANTOM_FETCH_URL = "https://github.com/Matt30098638/Phantom-fetch/archive/refs/heads/main.zip"

def install_dependencies():
    """Install required Python packages"""
    print("Installing required Python packages...")
    for package in DEPENDENCIES:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def download_and_extract_phantom_fetch():
    """Download and extract Phantom-fetch repository to INSTALL_PATH"""
    print("Downloading Phantom-fetch repository...")
    urllib.request.urlretrieve(PHANTOM_FETCH_URL, "phantom_fetch.zip")

    print(f"Extracting Phantom-fetch to {INSTALL_PATH}...")
    with zipfile.ZipFile("phantom_fetch.zip", 'r') as zip_ref:
        zip_ref.extractall(INSTALL_PATH)

    os.remove("phantom_fetch.zip")
    print("Phantom-fetch downloaded and extracted.")

def compile_to_exe():
    """Compile the project into an .exe file using PyInstaller"""
    print("Compiling the project into an .exe with PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", os.path.join(INSTALL_PATH, "main.py")])
    print("Compilation complete. Executable created in the 'dist' folder.")

def download_and_install_jackett():
    """Download and install Jackett for Windows"""
    if platform.system() == "Windows":
        print("Downloading Jackett for Windows...")
        jackett_zip_path = "Jackett.zip"
        urllib.request.urlretrieve(JACKETT_WINDOWS_URL, jackett_zip_path)
        
        print("Extracting Jackett...")
        with zipfile.ZipFile(jackett_zip_path, 'r') as zip_ref:
            install_dir = os.path.join(os.getenv('ProgramFiles'), 'Jackett')
            os.makedirs(install_dir, exist_ok=True)
            zip_ref.extractall(install_dir)
        
        print(f"Jackett installed to {install_dir}")
        os.remove(jackett_zip_path)
        
        webbrowser.open("http://localhost:9117")

    else:
        print("Unsupported OS for automated Jackett installation.")
        
def download_and_install_qbittorrent():
    """Download and install qBittorrent for Windows"""
    if platform.system() == "Windows":
        print("Please download and install qBittorrent manually from: https://www.qbittorrent.org/download.php")
        webbrowser.open(QBITTORRENT_WINDOWS_URL)
    else:
        print("Unsupported OS for automated qBittorrent installation.")

def is_tool_installed(name):
    """Check if a command-line tool is installed on Windows"""
    return os.path.exists(os.path.join(os.getenv("ProgramFiles"), name))

def check_prerequisites():
    """Check for prerequisite installations (Jackett and qBittorrent) and install if missing"""
    missing_tools = []

    # Check for Jackett installation
    if not is_tool_installed("Jackett"):
        print("Jackett is not installed.")
        missing_tools.append("Jackett")
        download_and_install_jackett()
    else:
        print("Jackett is installed.")

    # Check for qBittorrent installation
    if not is_tool_installed("qBittorrent"):
        print("qBittorrent is not installed.")
        missing_tools.append("qBittorrent")
        download_and_install_qbittorrent()
    else:
        print("qBittorrent is installed.")

    if missing_tools:
        print("\nThe following tools were installed during setup:", ", ".join(missing_tools))
    else:
        print("All prerequisites are already installed.")

    return True

def authenticate_with_microsoft():
    """Authenticate with Microsoft Graph and retrieve tokens"""
    print("Authenticating with Microsoft Graph...")

    # Prompt user for client and tenant information
    client_id = input("Enter your Microsoft Graph Client ID: ").strip()
    tenant_id = input("Enter your Microsoft Graph Tenant ID: ").strip()
    authority = f"{GRAPH_AUTHORITY}{tenant_id}"

    # Create a public MSAL client application
    app = PublicClientApplication(
        client_id=client_id,
        authority=authority,
    )

    # Open the browser for user login and permissions
    flow = app.initiate_device_flow(scopes=GRAPH_SCOPE)
    if "user_code" not in flow:
        raise Exception("Failed to create device flow")

    print(f"Please visit {flow['verification_uri']} and enter the code: {flow['user_code']}")
    webbrowser.open(flow["verification_uri"])

    # Retrieve token after successful authentication
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        print("Microsoft Graph authentication successful.")
        return {
            "client_id": client_id,
            "tenant_id": tenant_id,
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "scopes": GRAPH_SCOPE,
        }
    else:
        print("Microsoft Graph authentication failed.")
        sys.exit(1)

def authenticate_with_spotify():
    """Authenticate with Spotify and retrieve tokens"""
    print("Authenticating with Spotify...")

    # Prompt user for Spotify credentials
    client_id = input("Enter your Spotify Client ID: ").strip()
    client_secret = input("Enter your Spotify Client Secret: ").strip()

    # Set up Spotipy's OAuth flow
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-library-read",  # Add any other Spotify scopes as needed
        open_browser=True
    )

    # Open browser for user login
    auth_url = sp_oauth.get_authorize_url()
    print(f"Opening browser for Spotify authorization at {auth_url}")
    webbrowser.open(auth_url)

    # Capture authorization response
    response_url = input("Paste the full redirect URL after authorization: ").strip()
    code = sp_oauth.parse_response_code(response_url)
    token_info = sp_oauth.get_access_token(code)

    if token_info:
        print("Spotify authentication successful.")
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": token_info['access_token'],
            "refresh_token": token_info['refresh_token'],
            "scope": sp_oauth.scope
        }
    else:
        print("Spotify authentication failed.")
        sys.exit(1)

def gather_configuration():
    """Collect API credentials and other configuration from the user"""
    config = {}

    # Jellyfin Credentials
    config['Jellyfin'] = {
        'server_url': input("Enter your Jellyfin Server URL (e.g., http://localhost:8096): ").strip(),
        'api_key': input("Enter your Jellyfin API Key: ").strip()
    }

    # qBittorrent Credentials
    config['qBittorrent'] = {
        'host': input("Enter your qBittorrent host (e.g., http://127.0.0.1:8080): ").strip(),
        'username': input("Enter your qBittorrent username: ").strip(),
        'password': input("Enter your qBittorrent password: ").strip()
    }

    # TMDb API Key
    config['TMDb'] = {'api_key': input("Enter your TMDb API Key: ").strip()}

    # Spotify Authentication
    config['Spotify'] = authenticate_with_spotify()

    # Microsoft Graph Authentication
    config["MicrosoftGraph"] = authenticate_with_microsoft()

    return config

def write_config_to_yaml(config):
    """Write the configuration to the downloaded config.yaml file"""
    os.makedirs(ASSETS_PATH, exist_ok=True)  # Ensure directory exists
    with open(CONFIG_FILE_PATH, 'w') as file:
        yaml.dump(config, file)
    print(f"Configuration saved to {CONFIG_FILE_PATH}")

def setup():
    """Main setup process"""
    print("Starting setup process...")

    # Step 1: Download and extract Phantom-fetch repository
    download_and_extract_phantom_fetch()

    # Step 2: Install Python dependencies
    install_dependencies()

    # Step 3: Check for Jackett and qBittorrent
    check_prerequisites()

    # Step 4: Gather configuration from the user
    config = gather_configuration()

    # Step 5: Write configuration to YAML file
    write_config_to_yaml(config)

    # Step 6: Compile the project to an executable
    compile_to_exe()

    print("\nSetup is complete! You can now run the compiled executable in the 'dist' folder.")

if __name__ == "__main__":
    setup()
