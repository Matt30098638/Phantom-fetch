# Phantom Fetch

**Phantom Fetch** is an automated media downloader and organizer that integrates with various APIs and services to manage movies, TV shows, and music. With Phantom Fetch, users can set up media download requests through configuration files and authenticate with Microsoft Graph and Spotify to sync requests from emails and playlists.

This repository includes a `setup.py` script to automate the installation and configuration process, ensuring all dependencies, tools, and APIs are set up for seamless usage.

## Features

- **Automated Media Downloads**: Download movies, TV shows, and music based on requests from configuration files.
- **Microsoft Graph and Spotify Integration**: Use Microsoft Graph to fetch download requests from emails and Spotify to access playlists.
- **Jackett and qBittorrent Integration**: Automatically searches for media using Jackett and downloads using qBittorrent.
- **Configuration and Setup Automation**: A `setup.py` script to handle prerequisites, API authentication, and compilation into an executable file for easy usage.
- **Executable Compilation**: Automates converting the Python scripts into a single `.exe` file for ease of distribution and use on Windows systems.

## Prerequisites

- **Python** 3.7 or later
- **Git** (for cloning the repository)
- **Jackett** (automatically installed if not detected)
- **qBittorrent** (automatically installed if not detected)
- **Spotify API** and **Microsoft Graph API** credentials (generated during setup)

## Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/Matt30098638/Phantom-fetch.git
cd Phantom-fetch
```

Then, execute the `setup.py` file, which will:

1. Download and extract the Phantom-fetch project into `C:\Torrenter`.
2. Install all required Python dependencies.
3. Install **Jackett** and **qBittorrent** if they’re not already installed.
4. Collect API keys and credentials for Microsoft Graph, Spotify, Jellyfin, and TMDb.
5. Save configurations in `C:\Torrenter\assets\config.yaml`.
6. Compile the project into an executable (`.exe`) file.

Run `setup.py`:

```bash
python setup.py
```

Follow the prompts to enter API keys and credentials. This will set up the environment and create the final executable in the `dist` folder.

## Configuration

The primary configuration file is `config.yaml`, located in `C:\Torrenter\assets\`. `setup.py` creates and populates this file with your provided API keys and service configurations. This file includes:

- **Jellyfin API Key** and **Server URL**
- **qBittorrent Host, Username, and Password**
- **TMDb API Key** for retrieving media metadata
- **Microsoft Graph and Spotify Authentication** for fetching email and playlist requests

The setup script configures these values during the installation, but you can edit them manually if needed.

## Usage

Once setup is complete and the executable is created:

1. Run the executable from the `dist` folder.
2. Phantom Fetch will start monitoring requests in emails (Microsoft Graph) and Spotify playlists.
3. Download requests will automatically search Jackett for available torrents and download them via qBittorrent.
4. After downloads complete, media files are organized according to their type (movies, TV shows, or music) and stored in their respective directories.

## How It Works

1. **Setup**: `setup.py` installs dependencies, downloads and sets up Jackett and qBittorrent, and collects API credentials. It then compiles the project into an executable.
2. **API Integrations**: Uses Microsoft Graph to fetch requests from emails, Spotify to read playlists, and TMDb to retrieve media metadata.
3. **Media Search and Download**: Sends search requests through Jackett, retrieves torrents, and downloads them using qBittorrent.
4. **Media Organization**: Organizes downloaded media files in directories based on type, using predefined structure.

## Project Structure

```
Phantom-fetch/
├── assets/
│   └── config.yaml        # Configuration file (generated during setup)
├── main.py                # Main execution file (compiled into .exe)
├── setup.py               # Setup script for installation and configuration
└── README.md              # Project documentation
```

## Requirements

This project requires the following dependencies (automatically installed by `setup.py`):

- `requests`
- `qbittorrent-api`
- `msal`
- `beautifulsoup4`
- `pyyaml`
- `spotipy`
- `pyinstaller`

## Notes

- **Windows Compatibility**: This project primarily targets Windows systems. Automated Jackett and qBittorrent installation currently supports Windows. For Linux/macOS, you may need to install these tools manually.
- **Security**: Ensure all API keys and tokens are stored securely and not shared publicly.

## Troubleshooting

- **Dependency Installation Issues**: If Python dependencies fail to install, ensure Python is added to your system path and that you have a stable internet connection.
- **API Authentication Failures**: Verify that all API credentials are correct and that the necessary permissions (scopes) are granted.
- **qBittorrent Manual Installation**: If qBittorrent fails to install automatically, download it from [qBittorrent's website](https://www.qbittorrent.org/download.php) and install it manually.

## License

This project is licensed under the MIT License.

## Author

Developed by [Matt Palmer](https://github.com/Matt30098638).
