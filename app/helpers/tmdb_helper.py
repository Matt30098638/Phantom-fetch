import requests
import logging
import re
from config import Config
from app import db  # Make sure to import your database instance
from app.models import Recommendation, PastRecommendation  # Import your SQLAlchemy model for recommendations
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TMDbHelper:
    def __init__(self):
        try:
            config = Config()
            self.api_key = config.TMDB_API_KEY
            if not self.api_key:
                raise ValueError("TMDb API key not found in the configuration.")
            self.base_url = 'https://api.themoviedb.org/3'
            self.image_base_url = self._get_image_base_url()
        except Exception as e:
            logging.error(f"Error initializing TMDbHelper: {e}")
            raise

    def _get_image_base_url(self):
        """Fetch the base URL for images from TMDb configuration."""
        config_url = f"{self.base_url}/configuration"
        params = {"api_key": self.api_key}
        config_data = self._make_request(config_url, params)
        if config_data:
            return config_data["images"]["secure_base_url"] + "w200"
        else:
            logging.error("Failed to retrieve TMDb image configuration.")
            return None

    def _make_request(self, url, params):
        """Helper method to make HTTP requests and handle errors."""
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logging.error(f"Request to {url} timed out.")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP request error for {url}: {e}")
            return None

    def generate_tmdb_url(self, media_type, tmdb_id, title):
        """Generate a TMDb URL based on media type, ID, and title."""
        base_url = "https://www.themoviedb.org"
        prefix = "/movie/" if media_type == "movie" else "/tv/"
        slug_title = re.sub(r'[^a-zA-Z0-9-]', '', title.replace(' ', '-').lower())  # Slugify the title
        return f"{base_url}{prefix}{tmdb_id}-{slug_title}"

    def recommendation_exists(self, original_title, recommended_title):
        """Checks if a recommendation already exists in the database."""
        exists_in_recommendations = db.session.query(
            db.exists().where(
                (Recommendation.media_title == original_title) &
                (Recommendation.related_media_title == recommended_title)
            )
        ).scalar()

        exists_in_past_recommendations = db.session.query(
            db.exists().where(
                (PastRecommendation.media_title == original_title) &
                (PastRecommendation.related_media_title == recommended_title)
            )
        ).scalar()

        return exists_in_recommendations or exists_in_past_recommendations

    def get_recommendations(self, title, media_type):
        """Fetch recommendations for a given title."""
        logging.info(f"Fetching recommendations for '{title}' as {media_type}")
        media_path = 'movie' if media_type.lower() == 'movie' else 'tv'
        search_url = f"{self.base_url}/search/{media_path}"
        params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": "false",
            "language": "en-US,en-GB"  # Limit to en-US and en-GB
        }
        search_response = self._make_request(search_url, params)

        if not search_response or not search_response.get("results"):
            logging.info(f"No results found for '{title}'")
            return []

        media_id = search_response["results"][0].get('id')
        if not media_id:
            logging.warning(f"Missing ID for media '{title}'")
            return []

        recommendation_url = f"{self.base_url}/{media_path}/{media_id}/recommendations"
        recommendation_response = self._make_request(recommendation_url, {"api_key": self.api_key, "language": "en-US,en-GB"})

        recommendations = []
        for rec in recommendation_response.get("results", []):
            # Skip entries without language metadata or not matching en-US/en-GB
            if rec.get('original_language') not in ['en', 'en-US', 'en-GB']:
                logging.info(f"Skipping recommendation with non-supported language: {rec.get('original_language')}")
                continue

            recommended_title = rec.get('title') if media_type == 'movie' else rec.get('name')
            if not rec.get('id') or not recommended_title:  # Ensure required data is present
                logging.warning(f"Skipping invalid recommendation data: {rec}")
                continue

            # Skip existing recommendations
            if self.recommendation_exists(title, recommended_title):
                logging.info(f"Skipping existing recommendation '{recommended_title}'")
                continue

            # Log thumbnail downloading issues
            thumbnail_url = None
            if rec.get('poster_path'):
                thumbnail_url = f"{self.image_base_url}{rec['poster_path']}"
            else:
                logging.warning(f"No poster available for recommendation '{recommended_title}'")

            recommendations.append({
                "title": recommended_title,
                "media_type": media_type,
                "url": self.generate_tmdb_url(media_type, rec['id'], recommended_title),
                "overview": rec.get('overview', 'No description available.'),
                "thumbnail_url": thumbnail_url
            })

        logging.info(f"Found {len(recommendations)} new recommendations for '{title}'")
        return recommendations

    def get_media_details(self, title, media_type):
        """
        Fetch detailed information for a specific movie or TV show by title.
        """
        logging.info(f"Fetching media details for '{title}' as {media_type}")
        media_path = 'movie' if media_type.lower() == 'movie' else 'tv'
        search_url = f"{self.base_url}/search/{media_path}"
        params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": "false",
            "language": "en-US,en-GB"
        }
        search_response = self._make_request(search_url, params)

        if not search_response or not search_response.get("results"):
            logging.warning(f"No details found for '{title}'")
            return None

        # Assuming the first result is the most relevant match
        return search_response["results"][0]
    
    def get_upcoming_movies(self, region="US"):
        today = datetime.now().strftime("%Y-%m-%d")
        three_months_later = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        # Add the region parameter to the request URL
        url = f"{self.base_url}/movie/upcoming?api_key={self.api_key}&language=en-US&region={region}"
        response = requests.get(url)
        response.raise_for_status()

        results = response.json().get('results', [])
        # Filter results for release dates between today and three months from now
        filtered_results = [
            movie for movie in results
            if movie.get('release_date') and today <= movie['release_date'] <= three_months_later
        ]
        return filtered_results

    def get_upcoming_tv_shows(self):
        """
        Fetch TV shows airing today using TMDb's /tv/airing_today endpoint.
        """
        endpoint = "/tv/airing_today"
        params = {
            "api_key": self.api_key,
            "language": "en-GB",  # Default to en-GB
            "page": 1  # Start with the first page
        }

        try:
            # Fetch all pages of results
            all_results = self.get_all_pages(endpoint, params)

            # Log the total number of results
            logging.info(f"Retrieved {len(all_results)} TV shows airing today.")
            return all_results

        except Exception as e:
            logging.error(f"Error fetching TV shows airing today: {e}")
            return []
    def get_all_pages(self, endpoint, params):
        """
        Fetch all pages of results from a paginated TMDb endpoint.
        """
        results = []
        try:
            while True:
                response = self._make_request(f"{self.base_url}{endpoint}", params)
                if not response or not response.get("results"):
                    break

                results.extend(response["results"])

                # Stop if we've reached the last page
                if response["page"] >= response["total_pages"]:
                    break

                # Move to the next page
                params['page'] += 1

            logging.info(f"Fetched a total of {len(results)} items from {endpoint}.")
            return results
        except Exception as e:
            logging.error(f"Error during pagination for {endpoint}: {e}")
            return []
