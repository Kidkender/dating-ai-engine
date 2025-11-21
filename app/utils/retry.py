from functools import wraps
from typing import Type, Tuple

from fastapi.logger import logger

def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    attempts += 1
                    
                    if attempts >= max_attempts:
                        logger.error(
                            f"Max retry attempts reached for {func.__name__}",
                            extra={
                                "attempts": attempts,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    logger.warning(
                        f"Retry attempt {attempts}/{max_attempts} for {func.__name__}",
                        extra={"delay": current_delay}
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator