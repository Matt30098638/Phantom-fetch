### **Media Management Flask Application Documentation**

---

#### **Project Overview**

The Media Management Flask application is a comprehensive solution for managing and processing media-related tasks. It leverages Python, Flask, and various helper libraries to interact with external services like qBittorrent, Jackett, and TMDB to provide an automated media download and management system. 

**Key Features:**
1. **Media Search and Downloads:** Search for torrents using Jackett and download them with qBittorrent.
2. **Recommendations:** Automatically generate recommendations for movies, TV shows, and other media using TMDB APIs.
3. **User Management:** Secure login and user management using Flask-Login.
4. **Task Scheduling:** Background tasks for processing requests and recommendations using APScheduler.
5. **Web-based Interface:** A simple and intuitive web interface for users to interact with the application.
6. **Logging and Monitoring:** Built-in logging for tracking errors and application events.

---

#### **Requirements**

- **Operating System:** Windows (Tested on Windows Server and Windows 10/11)
- **Python Version:** Python 3.13.x
- **Hosting Options:**
  - Flask development server (for testing)
  - Waitress (for production)
- **Database:** SQLite (default) or another SQLAlchemy-compatible database (e.g., PostgreSQL, MySQL).

---

#### **Dependencies**

Install all the required dependencies using `pip` from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

**Key Dependencies:**
1. **Flask**: Web framework for building the application.
2. **Flask-Login**: For user authentication and session management.
3. **Flask-WTF**: For CSRF protection and form handling.
4. **SQLAlchemy**: ORM for interacting with the database.
5. **Flask-Migrate**: For database migrations.
6. **APScheduler**: For background job scheduling.
7. **qBittorrent API**: For interacting with the qBittorrent client.
8. **Jackett API**: For torrent searching.
9. **TMDB API**: For fetching movie and TV show data.

---

#### **Configuration**

All configuration is managed via the `Config` class in `config.py`:
```python
class Config:
    SECRET_KEY = "your_secret_key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///media_management.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TMDB_API_KEY = "your_tmdb_api_key"
    JACKETT_API_KEY = "your_jackett_api_key"
    QBITTORRENT_URL = "http://127.0.0.1:8080"
    QBITTORRENT_USERNAME = "admin"
    QBITTORRENT_PASSWORD = "password"
```

Update the `Config` class with your API keys and service configurations before running the application.

---

#### **How to Run the Application**

1. **Clone the Repository**
   ```bash
   git clone https://your-repo-url.git
   cd Media_management
   ```

2. **Set up a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # For Linux/macOS
   venv\Scripts\activate     # For Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up the Database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration."
   flask db upgrade
   ```

5. **Run the Application**
   For development:
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

   For production (Waitress):
   ```bash
   waitress-serve --host=0.0.0.0 --port=5000 app:create_app
   ```

6. **Access the Application**
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

#### **Application Functionality**

1. **Dashboard**
   - Provides an overview of the application and key actions.

2. **Media Management**
   - Search for torrents using Jackett.
   - Download media files via qBittorrent.

3. **Recommendations**
   - Fetch personalized media recommendations from TMDB.
   - Mark recommendations as ignored or accepted.

4. **Requests**
   - Manage media download requests (e.g., movies, TV shows).
   - Process pending requests.

5. **Background Tasks**
   - Automated scheduling for:
     - Generating daily recommendations.
     - Processing pending requests.

6. **User Authentication**
   - Secure login/logout functionality using Flask-Login.

---

#### **File Structure**

```plaintext
Media_management/
│
├── app/
│   ├── __init__.py         # App factory and initialization
│   ├── models.py           # Database models
│   ├── routes/             # Blueprints for application routes
│   │   ├── auth_routes.py
│   │   ├── web_routes.py
│   │   ├── jellyfin_routes.py
│   │   └── request_processing_routes.py
│   ├── templates/          # HTML templates for Flask
│   ├── static/             # Static files (CSS, JS, images)
│   └── helpers/            # Helper modules for Jackett, TMDB, etc.
│
├── config.py               # Application configuration
├── requirements.txt        # Python dependencies
├── run.py                  # Main entry point for Flask
├── logs/                   # Logs directory
└── migrations/             # Database migration files
```

---

#### **Logging**

Logs are stored in the `logs/` directory. The app uses a `RotatingFileHandler` to manage log files, ensuring they don't grow too large.

Example configuration:
```python
LOG_DIR = "./logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
```

Logs include:
- Scheduler task logs.
- Application errors.
- Successful or failed requests to external APIs.

---

#### **Use Cases**

1. **Media Enthusiasts:**
   Automates the process of discovering, downloading, and organizing movies and TV shows.

2. **Home Media Servers:**
   Can be integrated with media servers like Plex or Jellyfin to manage content libraries.

3. **Efficient Torrent Management:**
   Combines the power of Jackett and qBittorrent for streamlined torrent searches and downloads.

---

#### **Future Improvements**

1. **Docker Support:**
   Add Docker configurations for easier deployment.

2. **Scalability:**
   Transition to PostgreSQL for larger datasets.

3. **Improved User Interface:**
   Enhance the web interface for a better user experience.

4. **Notifications:**
   Add email or push notifications for completed downloads or updates.

5. **Custom Media Organization:**
   Provide advanced options for organizing media into specific folder structures.

