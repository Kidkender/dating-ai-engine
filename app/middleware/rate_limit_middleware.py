from typing import Awaitable, Callable
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime

from starlette.responses import Response


class RateLimiter:
    def __init__(self) -> None:
        self.clients = defaultdict(lambda: {
            "tokens": 100,
            "last_update": datetime.now()
        })
        self.max_tokens = 100
        self.refill_rate = 10  # tokens per second
        
    def _refill_tokens(self, client_id: str):
        now = datetime.now()
        client = self.clients[client_id]
        
        time_passed = (now - client["last_update"]).total_seconds()
        tokens_to_add = time_passed * self.refill_rate
        
        client["tokens"] = min(
            self.max_tokens,
            client["tokens"] + tokens_to_add
        )
        client["last_update"] = now
        
    def allow_request(self, client_id: str, cost = 1) -> bool: 
        self._refill_tokens(client_id)
        
        if self.clients[client_id]["tokens"] >= cost:
            self.clients[client_id]["tokens"] -= cost
            return True
        return False

rate_limiter = RateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    #   return await super().dispatch(request, call_next)
    client_id = request.client.host
    
    if request.url.path in ["/health", "/docs"]:
        return await call_next(request)
    
    if not rate_limiter.allow_request(client_id):
        return JSONResponse(
            status_code=429,
            content= {
                   "error_code": "error.rate-limit.exceeded",
                    "message": "Too many requests",
                    "retry_after": 10
            }
        )
    return await call_next(request)