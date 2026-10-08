"""
Standard API response envelope.
Every API response is wrapped in this consistent structure.
"""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    
    Success:
        {"success": true, "data": {...}}
    
    Error:
        {"success": false, "error": {"code": "...", "message": "..."}}
    """
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, code: str, message: str, details: Optional[dict] = None) -> "APIResponse":
        return cls(
            success=False,
            error=ErrorDetail(code=code, message=message, details=details),
        )
