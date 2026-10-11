from typing import Any, Dict, Optional
from fastapi import status


class AppException(Exception):
    """Base application exception for all domain and operational errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class FileValidationError(AppException):
    def __init__(
        self,
        message: str,
        code: str = "FILE_VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnsupportedFileTypeError(FileValidationError):
    def __init__(
        self,
        message: str = "Only .kml and .zip Shapefile uploads are supported.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            details=details,
        )


class EmptyFileError(FileValidationError):
    def __init__(
        self,
        message: str = "Uploaded file is empty (0 bytes).",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="EMPTY_FILE",
            details=details,
        )


class FileSizeExceededError(AppException):
    def __init__(
        self,
        max_size_bytes: int,
        actual_size_bytes: Optional[int] = None,
    ) -> None:
        max_mb = max_size_bytes / (1024 * 1024)
        super().__init__(
            code="FILE_SIZE_EXCEEDED",
            message=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={
                "max_size_bytes": max_size_bytes,
                "actual_size_bytes": actual_size_bytes,
            },
        )


class SecurityValidationError(AppException):
    def __init__(
        self,
        message: str,
        code: str = "SECURITY_VIOLATION",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class PathTraversalError(SecurityValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(
            code="PATH_TRAVERSAL_DETECTED",
            message="Archive contains illegal paths attempting directory traversal.",
            details={"filename": filename},
        )


class ZipBombError(SecurityValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="ZIP_BOMB_DETECTED",
            message=message,
        )


class GeospatialProcessingError(AppException):
    def __init__(
        self,
        message: str,
        code: str = "GEOSPATIAL_PROCESSING_ERROR",
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            details=details,
        )


class InvalidShapefileArchiveError(GeospatialProcessingError):
    def __init__(self, message: str, missing_extensions: Optional[list] = None) -> None:
        super().__init__(
            code="INVALID_SHAPEFILE_ARCHIVE",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"missing_extensions": missing_extensions or []},
        )


class CorruptFileError(GeospatialProcessingError):
    def __init__(self, message: str = "The uploaded file is corrupt or unreadable.") -> None:
        super().__init__(
            code="CORRUPT_FILE",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class EntityNotFoundError(AppException):
    def __init__(
        self,
        entity_name: str,
        entity_id: str,
    ) -> None:
        super().__init__(
            code=f"{entity_name.upper()}_NOT_FOUND",
            message=f"{entity_name} with ID '{entity_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity": entity_name, "id": entity_id},
        )
