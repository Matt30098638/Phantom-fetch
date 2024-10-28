# utils/tmdb_helper.py
import requests
import yaml
import os
import logging

logging.basicConfig(level=logging.INFO)

class TMDbHelper:
    def __init__(self, config_path):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        tmdb_config = config.get('TMDb', {})
        self.api_key = tmdb_config.get('api_key')
        self.base_url = 'https://api.themoviedb.org/3'

    def classify_title(self, title):
        """
        Searches for a given title in TMDb and classifies it as 'movie' or 'tv'.
        """
        TMDB_SEARCH_URL = f"{self.base_url}/search/multi"
        try:
            response = requests.get(TMDB_SEARCH_URL, params={
                "api_key": self.api_key,
                "query": title,
                "include_adult": "false"
            })

            # Check if the response is successful
            if response.status_code != 200:
                logging.error(f"TMDb API error: {response.status_code} - {response.text}")
                return None

            search_results = response.json().get("results", [])
            if not search_results:
                logging.info(f"No results found for title: {title}")
                return None

            # Return the type of media (movie or tv)
            first_result = search_results[0]
            media_type = first_result.get("media_type")

            if media_type == "movie":
                logging.info(f"Movie found: {first_result.get('title')} (TMDb ID: {first_result.get('id')})")
                return "movie"
            elif media_type == "tv":
                logging.info(f"TV show found: {first_result.get('name')} (TMDb ID: {first_result.get('id')})")
                return "tv"
            else:
                logging.info(f"Unknown media type for title: {title} - media_type: {media_type}")
                return None

        except Exception as e:
            logging.error(f"Error while classifying title '{title}' with TMDb: {e}")
            return None

    def get_media_details(self, title, media_type):
        """
        Get detailed information for a specific media (either a movie or a TV show).
        """
        # Use the appropriate search endpoint based on media type
        TMDB_SEARCH_URL = f"{self.base_url}/search/{media_type}"
        try:
            response = requests.get(TMDB_SEARCH_URL, params={
                "api_key": self.api_key,
                "query": title,
                "include_adult": "false"
            })

            # Check if the response is successful
            if response.status_code != 200:
                logging.error(f"TMDb API call failed: {response.status_code} - {response.content.decode()}")
                return None

            search_results = response.json().get("results", [])
            if not search_results:
                logging.info(f"No results found for title: {title}")
                return None

            # Return the first match details
            logging.info(f"Media details found for '{title}': {search_results[0]}")
            return search_results[0]

        except Exception as e:
            logging.error(f"Error fetching media details for '{title}' from TMDb: {e}")
            return None
    def is_part_of_franchise(self, media_details):
        """
        Checks if the given movie is part of a series or franchise.
        """
        collection_id = media_details.get('belongs_to_collection')
        return collection_id is not None

    def get_franchise_movies(self, media_details):
        """
        Gets the list of movies from a collection/franchise if the movie belongs to one.
        """
        collection = media_details.get('belongs_to_collection', {})
        collection_id = collection.get('id')
        if not collection_id:
            return []

        url = f"{self.base_url}/collection/{collection_id}"
        params = {"api_key": self.api_key}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                movies = response.json().get('parts', [])
                return movies
            else:
                logging.error(f"Failed to fetch franchise movies. Status code: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Error while fetching franchise movies: {e}")
            return []