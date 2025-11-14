from io import BytesIO
import logging
from typing import Optional
from PIL import Image
from app.utils.http_client import http_client

from ..schemas.sync import DatingAppUser


logger = logging.getLogger(__name__)


class DatingAppClient:
    """Client for interacting with dating app api"""

    def __init__(
        self,
        base_url: str,
        image_base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize dating app client

        Args:
            base_url: Base URL of dating app API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.image_base_url = image_base_url
        self.api_key = api_key
        self.timeout = timeout

        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"  # type: ignore

    async def fetch_all_users(self, limit: Optional[int] = 1000) -> list[DatingAppUser]:
        """
        Fetch all users from dating app

        Args:
            limit: Optional limit on number of users to fetch

        Returns:
            List of DatingAppUser objects
        """
        try:
            params = {}
            if limit is not None:
                params["limit"] = limit
            
            response = await http_client.get(
                f"{self.base_url}/api/dating/users",
                headers=self.headers,
                params=params,
            )

            response.raise_for_status()
            response_json = response.json()

            if isinstance(response_json, dict) and "data" in response_json:
                user_data_list = response_json["data"]
                logger.info(
                    f"Parsed response with status: {response_json.get('status')}"
                )
            else:
                user_data_list = response_json

            users = []
            for user_data in user_data_list:
                try:
                    user = DatingAppUser.model_validate(user_data)
                    users.append(user)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse user {user_data.get('userEmail', 'unknown')}: {e}"
                    )
                    continue

            logger.info(f"Successfully fetched {len(users)} users from dating app")
            return users

        except Exception as e:
            logger.error(f"Error fetching users: {e}", exc_info=True)
            raise
    async def fetch_user_by_id(self, user_id: str) -> Optional[DatingAppUser]:
        """
        Fetch single user by ID

        Args:
            user_id: User ID to fetch

        Returns:
            DatingAppUser or None if not found
        """
        try:
            response = await http_client.get(
                f"{self.base_url}/api/admin/users/{user_id}",
                headers=self.headers,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return DatingAppUser(**response.json())

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
            raise

    async def download_image(self, image_path: str) -> Optional[Image.Image]:
        """
        Download image from dating app

        Args:
            image_path: Image path from dating app

        Returns:
            PIL Image object or None if download fails
        """
        try:
            if image_path.startswith("http"):
                full_url = image_path
            else:
                clean_path = image_path.lstrip("/")
                full_url = f"{self.image_base_url}/{clean_path}"

            logger.debug(f"Downloading image from: {full_url}")

            download_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }

            response = await http_client.get(
                full_url,
                headers=download_headers,
            )
            
            response.raise_for_status()

            # Load image from bytes
            image = Image.open(BytesIO(response.content))
            image = image.convert("RGB")

            logger.debug(f"Successfully downloaded image: {image_path}")
            return image

        except Exception as e:
            logger.warning(f"Error downloading image {image_path}: {e}")
            return None

    async def verify_connection(self) -> bool:
        """
        Verify connection to dating app API

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = await http_client.get(
                f"{self.base_url}/api/auth/healthCheck",
                headers=self.headers,
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False