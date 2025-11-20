from typing import Generic, List, TypeVar

from pydantic import BaseModel


T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginationResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int