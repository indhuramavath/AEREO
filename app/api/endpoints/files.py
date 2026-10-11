from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.file import FileDetailResponse, FileListResponse, FileUploadResponse
from app.schemas.measurement import FileMeasurementsResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Geospatial Files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process geospatial dataset (.kml or .zip Shapefile)",
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.kml or .zip shapefile)"),
    db: Session = Depends(get_db),
):
    """
    Accepts a .kml or .zip Shapefile archive, validates integrity/security constraints,
    reprojects geometries to the optimal metric CRS, and computes feature measurements.
    """
    return await FileService.save_and_process_upload(upload_file=file, db=db)


@router.get(
    "",
    response_model=FileListResponse,
    summary="List all uploaded geospatial files",
)
def list_files(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
):
    """Retrieves paginated list of previously uploaded datasets."""
    return FileService.list_files(db=db, limit=limit, offset=offset)


@router.get(
    "/{file_id}",
    response_model=FileDetailResponse,
    summary="Retrieve dataset processing details and status",
)
def get_file_details(
    file_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves metadata and processing status for a specific dataset ID."""
    return FileService.get_file_by_id(file_id=file_id, db=db)


@router.get(
    "/{file_id}/measurements",
    response_model=FileMeasurementsResponse,
    summary="Retrieve geometric measurements and summary for a dataset",
)
def get_file_measurements(
    file_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves feature-level measurements (area in m² for polygons, length in m for lines)
    and aggregate dataset summary statistics.
    """
    return FileService.get_measurements_by_file_id(file_id=file_id, db=db)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset and its measurements",
)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
):
    """Deletes the stored file from disk and cascades deletion of its measurement records."""
    FileService.delete_file(file_id=file_id, db=db)
    return None
