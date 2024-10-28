import requests
import yaml
import logging
import os

class JackettHelper:
    def __init__(self, config_path='config.yaml'):
        # Load configuration from YAML
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        jackett_config = config.get('Jackett', {})

        self.api_key = jackett_config.get('api_key', '')
        self.server_url = jackett_config.get('server_url', '')
        self.categories = jackett_config.get('categories', {})

        if not self.api_key or not self.server_url:
            raise ValueError("Jackett configuration is missing 'api_key' or 'server_url'.")

    def search_jackett(self, query, category="Music"):
        """Search for a torrent using Jackett with filtering."""
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

    # Search for a music torrent
    magnet_uri = jackett_helper.search_jackett("Your Query", category="Music")
    if magnet_uri:
        print(f"Magnet URI: {magnet_uri}")
    else:
        print("No suitable torrent found.")
