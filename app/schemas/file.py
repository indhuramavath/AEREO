from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import PaginationMeta


class FileUploadResponse(BaseModel):
    id: str = Field(..., description="Unique UUID assigned to the uploaded geospatial dataset")
    filename: str = Field(..., description="Sanitized original filename")
    file_type: str = Field(..., description="Detected file type ('kml' or 'shapefile')")
    file_size_bytes: int = Field(..., description="File size in bytes")
    feature_count: int = Field(..., description="Total count of geospatial features parsed")
    source_crs: Optional[str] = Field(None, description="Source Coordinate Reference System (e.g., EPSG:4326)")
    projected_crs: Optional[str] = Field(None, description="Calculated projected CRS for metric measurements")
    status: str = Field(..., description="Processing status (PENDING, PROCESSING, COMPLETED, FAILED)")
    processing_time_ms: Optional[float] = Field(None, description="Total backend processing latency in milliseconds")
    created_at: datetime = Field(..., description="Timestamp when file was uploaded and parsed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "e93838dc-369b-449e-baef-cbb09d3b5b63",
                "filename": "site_survey.kml",
                "file_type": "kml",
                "file_size_bytes": 10420,
                "feature_count": 15,
                "source_crs": "EPSG:4326",
                "projected_crs": "EPSG:32643",
                "status": "COMPLETED",
                "processing_time_ms": 28.5,
                "created_at": "2026-10-07T14:40:00Z",
            }
        }
    }


class FileDetailResponse(FileUploadResponse):
    error_message: Optional[str] = Field(None, description="Failure diagnostic message if processing failed")
    updated_at: datetime = Field(..., description="Timestamp when file metadata was last modified")


class FileListItem(FileUploadResponse):
    pass


class FileListResponse(BaseModel):
    items: List[FileListItem] = Field(..., description="List of uploaded files")
    pagination: PaginationMeta = Field(..., description="Pagination details")
