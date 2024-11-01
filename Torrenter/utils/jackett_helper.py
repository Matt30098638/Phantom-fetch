import requests
import yaml
import logging
import os
import subprocess
import time

class JackettHelper:
    def __init__(self, config_path='config.yaml'):
        # Load configuration from YAML
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        jackett_config = config.get('Jackett', {})

        self.api_key = jackett_config.get('api_key', '')
        self.server_url = jackett_config.get('server_url', '')
        self.categories = jackett_config.get('categories', {})
        self.jackett_path = jackett_config.get('path', '')  # Path to Jackett executable

        if not self.api_key or not self.server_url or not self.jackett_path:
            raise ValueError("Jackett configuration is missing 'api_key', 'server_url', or 'path'.")

    def check_running(self):
        """Check if Jackett is running by sending a request to its server URL."""
        try:
            response = requests.get(self.server_url)
            return response.status_code == 200
        except requests.ConnectionError:
            logging.warning("Jackett is not running.")
            return False

    def start_service(self):
        """Attempt to start Jackett service if it's not running."""
        if not os.path.exists(self.jackett_path):
            logging.error(f"Jackett path not found: {self.jackett_path}")
            return False

        try:
            logging.info("Starting Jackett service...")
            subprocess.Popen([self.jackett_path])  # Launch Jackett
            time.sleep(5)  # Wait briefly to allow service to start
            if self.check_running():
                logging.info("Jackett started successfully.")
                return True
            else:
                logging.error("Failed to start Jackett.")
                return False
        except Exception as e:
            logging.error(f"Error starting Jackett: {e}")
            return False

    def search_jackett(self, query, category="Music"):
        """Search for a torrent using Jackett with filtering."""
        if not self.check_running():
            logging.info("Jackett is not running; attempting to start...")
            if not self.start_service():
                logging.error("Unable to start Jackett service. Aborting search.")
                return None

        try:
            # Set the category ID from config
            category_id = self.categories.get(category, "")
            if not category_id:
                raise ValueError(f"Category '{category}' not found in Jackett configuration.")

            # Construct the search URL
            url = f"{self.server_url}/api/v2.0/indexers/all/results"
            params = {
                'apikey': self.api_key,
                'Query': query,
                'Category[]': category_id
            }

            # Send the request to Jackett API
            response = requests.get(url, params=params)
            response.raise_for_status()

            results = response.json().get('Results', [])

            # Filter results to only include those with at least 5 seeders
            filtered_results = [result for result in results if result.get('Seeders', 0) >= 5]

            if filtered_results:
                # Sort results by number of seeders (descending)
                sorted_results = sorted(filtered_results, key=lambda x: x.get('Seeders', 0), reverse=True)
                best_result = sorted_results[0]
                
                # Log the best result and return its magnet URI
                logging.info(f"Selected torrent: {best_result.get('Title')} with {best_result.get('Seeders')} seeders.")
                return best_result.get('MagnetUri')

            logging.info(f"No suitable results found on Jackett for: {query} with at least 5 seeders.")
            return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Error during Jackett request for '{query}': {e}")
            return None
        except Exception as e:
            logging.error(f"General error during Jackett search for '{query}': {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Load the config path dynamically or use default
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../assets/config.yaml')  # Adjusted path to locate config file

    # Initialize JackettHelper
    jackett_helper = JackettHelper(config_path=CONFIG_FILE)

    # Check if Jackett is running, start it if necessary, and search for a music torrent
    if jackett_helper.check_running() or jackett_helper.start_service():
        magnet_uri = jackett_helper.search_jackett("Your Query", category="Music")
        if magnet_uri:
            print(f"Magnet URI: {magnet_uri}")
        else:
            print("No suitable torrent found.")
    else:
        print("Jackett service could not be started.")
