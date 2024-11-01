import requests
import re
import logging
import time
from config import config

class JackettHelper:
    def __init__(self):
        jackett_config = config.get_jackett_config()
        self.api_key = jackett_config.get('api_key', '')
        self.server_url = jackett_config.get('server_url', '')
        self.categories = jackett_config.get('categories', {})
        self.failed_search_cache = {}

        if not self.api_key or not self.server_url:
            raise ValueError("Jackett configuration is missing 'api_key' or 'server_url'.")

    def search_jackett(self, query, min_seeders=5, category="Movies"):
        """Search for a torrent using Jackett with filtering."""
        cache_expiry = 60 * 60  # 1 hour cache for failed searches
        current_time = time.time()
        if query in self.failed_search_cache:
            last_attempt = self.failed_search_cache[query]
            if current_time - last_attempt < cache_expiry:
                logging.info(f"Skipping search for '{query}' due to recent failure.")
                return None

        try:
            # Ensure category ID is set
            category_id = self.categories.get(category, "")
            if not category_id:
                raise ValueError(f"Category '{category}' not found in Jackett configuration.")

            url = f"{self.server_url}/api/v2.0/indexers/all/results"
            params = {
                'apikey': self.api_key,
                'Query': self.format_query(query, category),
                'Category[]': category_id
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            results = response.json().get('Results', [])

            # Filter by seeders
            filtered_results = [result for result in results if result.get('Seeders', 0) >= min_seeders]

            if filtered_results:
                # Sort by seeders and return the best result
                sorted_results = sorted(filtered_results, key=lambda x: x.get('Seeders', 0), reverse=True)
                logging.info(f"Selected torrent: {sorted_results[0].get('Title')} with {sorted_results[0].get('Seeders')} seeders.")
                return sorted_results[0].get('MagnetUri')
            else:
                logging.info(f"No suitable results found on Jackett for: {query} with at least {min_seeders} seeders.")
                self.failed_search_cache[query] = current_time
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Jackett search error for '{query}': {e}")
            self.failed_search_cache[query] = current_time
            return None

    @staticmethod
    def format_query(query, category):
        """Format query for improved compatibility with Jackett searches."""
        if category == "Movies":
            query = re.sub(r'\(\d{4}\)$', '', query)
            query = re.sub(r'[^\w\s]', '', query)
        return query.strip()
