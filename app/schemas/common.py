from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Unique error identifier code")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context-specific error details")


class ErrorResponse(BaseModel):
    error: ErrorDetail

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": "Only .kml and .zip Shapefile uploads are supported.",
                    "details": {"allowed_extensions": [".kml", ".zip"]},
                }
            }
        }
    }


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total number of items available")
    limit: int = Field(..., description="Page limit requested")
    offset: int = Field(..., description="Page offset requested")
