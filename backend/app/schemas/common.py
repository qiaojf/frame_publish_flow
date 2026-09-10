from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    data: None = None
    message: str
    error_code: str


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
