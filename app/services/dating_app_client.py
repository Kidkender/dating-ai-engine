from io import BytesIO
import httpx
import logging
from typing import Optional
from PIL import Image

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
        self.api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NzI5YzI5NzgxMmU4NmQ3M2I1NTM0MjEiLCJ1c2VyRW1haWwiOiJ2dW9uZ0B5b3BtYWlsLmNvbSIsInVzZXJOYW1lIjoiVnVvbmciLCJpc0FkbWluIjp0cnVlLCJ1c2VyT25ib2FyZGluZyI6ImRvbmUiLCJwcm9maWxlVHlwZSI6ImJ1c2luZXNzIiwiYnVzaW5lc3NQcm9maWxlIjoiIiwiY29tbW9uT25ib2FyZGluZyI6dHJ1ZSwiYnVzaW5lc3NPbmJvYXJkaW5nIjp0cnVlLCJsb2dpblNlc3Npb25Qcm9maWxlVHlwZSI6ImluZGl2aWR1YWwiLCJpYXQiOjE3NjI3NDQ2MzB9.3T_jxjlZywgxPFi0VyMIDgpiPT3SAYkRKhYK6ZheLa4"
        self.timeout = timeout

        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"  # type: ignore

    async def fetch_all_users(self, limit: Optional[int] = None) -> list[DatingAppUser]:
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

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/admin/users",
                    headers=self.headers,  # type: ignore
                    params=params,  # type: ignore
                )
                response.raise_for_status()
                response_json = response.json()

                if isinstance(response_json, dict) and "data" in response_json:
                    user_data_list = response_json["data"]
                    logger.info(
                        f"Parsed response with status: {response_json.get('status')}"
                    )
                else:
                    # Fallback: assume response is directly the user array
                    user_data_list = response_json

                users = []
                for user_data in user_data_list:
                    try:
                        # Pydantic will automatically pick only defined fields
                        user = DatingAppUser.model_validate(user_data)
                        users.append(user)
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse user {user_data.get('userEmail', 'unknown')}: {e}"
                        )
                        continue

                logger.info(f"Successfully fetched {len(users)} users from dating app")
                return users  # type: ignore

        except httpx.HTTPError as e:
            logger.error(f"Http error fetching users: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise

    async def fetch_user_by_id(self, user_id: str) -> Optional[DatingAppUser]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/admin/users/{user_id}", headers=self.headers  # type: ignore
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                return DatingAppUser(**response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            raise

    async def download_image(self, image_path: str) -> Optional[Image.Image]:
        """
        Download image from dating app

        Args:
            image_path: Image path from dating app (e.g., "images/1746613443481_1000003282.png")

        Returns:
            PIL Image object or None if download fails
        """
        try:
            # Construct full URL
            # If image_path already starts with http, use as is
            if image_path.startswith("http"):
                full_url = image_path
            else:
                # Remove leading slash if exists
                clean_path = image_path.lstrip("/")
                # Construct full URL with base_url
                full_url = f"{self.image_base_url}/{clean_path}"

            logger.debug(f"Downloading image from: {full_url}")

            download_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(full_url, headers=download_headers)  # type: ignore
                response.raise_for_status()

                # Load image from bytes
                image = Image.open(BytesIO(response.content))
                image = image.convert("RGB")

                logger.debug(f"Successfully downloaded image: {image_path}")
                return image

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error downloading image {image_path}: {e}")
            return None
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
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/api/auth/healthCheck", headers=self.headers  # type: ignore
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
