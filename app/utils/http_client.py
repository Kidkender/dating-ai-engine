import logging
from typing import Any, Dict, Optional
import httpx
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


class HTTPClient:
    """Singleton HTTP client for making external API calls"""

    _instance: Optional['HTTPClient'] = None
    _client: Optional[httpx.AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.DATING_APP_TIMEOUT,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0,
                ),
                http2=True,  # Enable HTTP/2 for better performance
            )
            logger.info("HTTP Client initialized with connection pooling")

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client instance"""
        if self._client is None:
            raise RuntimeError("HTTP client not initialized")
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP Client closed")

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make GET request

        Args:
            url: Request URL
            headers: Optional headers
            params: Optional query parameters
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response object
        """
        try:
            response = await self.client.get(
                url,
                headers=headers,
                params=params,
                **kwargs
            )
            
            logger.debug(
                f"GET {url} -> {response.status_code}",
                extra={
                    "url": url,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            )
            
            return response

        except httpx.TimeoutException as e:
            logger.error(f"Timeout on GET {url}", exc_info=True)
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error on GET {url}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error on GET {url}: {e}", exc_info=True)
            raise

    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make POST request

        Args:
            url: Request URL
            headers: Optional headers
            json: Optional JSON body
            data: Optional form data
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response object
        """
        try:
            response = await self.client.post(
                url,
                headers=headers,
                json=json,
                data=data,
                **kwargs
            )
            
            logger.debug(
                f"POST {url} -> {response.status_code}",
                extra={
                    "url": url,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            )
            
            return response

        except httpx.TimeoutException as e:
            logger.error(f"Timeout on POST {url}", exc_info=True)
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error on POST {url}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error on POST {url}: {e}", exc_info=True)
            raise

    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make PUT request"""
        try:
            response = await self.client.put(
                url,
                headers=headers,
                json=json,
                **kwargs
            )
            
            logger.debug(f"PUT {url} -> {response.status_code}")
            return response

        except Exception as e:
            logger.error(f"Error on PUT {url}: {e}", exc_info=True)
            raise

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make DELETE request"""
        try:
            response = await self.client.delete(
                url,
                headers=headers,
                **kwargs
            )
            
            logger.debug(f"DELETE {url} -> {response.status_code}")
            return response

        except Exception as e:
            logger.error(f"Error on DELETE {url}: {e}", exc_info=True)
            raise


# Global singleton instance
http_client = HTTPClient()


@asynccontextmanager
async def get_http_client():
    """
    Context manager for HTTP client
    
    Usage:
        async with get_http_client() as client:
            response = await client.get("https://api.example.com")
    """
    try:
        yield http_client
    finally:
        pass  # Don't close on each use, only on app shutdown


async def close_http_client():
    """Close HTTP client on application shutdown"""
    await http_client.close()