from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import time
from typing import List, Optional, Tuple
import uuid

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    EmptyFileError,
    EntityNotFoundError,
    FileSizeExceededError,
    UnsupportedFileTypeError,
)
from app.core.logging import logger
from app.models.file import FileProcessingStatus, FileType, UploadedFileModel
from app.models.measurement import FeatureMeasurementModel
from app.schemas.file import FileDetailResponse, FileListItem, FileListResponse, FileUploadResponse
from app.schemas.measurement import FeatureMeasurementItem, FileMeasurementsResponse, MeasurementSummary
from app.services.geospatial import GeospatialProcessor


class FileService:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Strip directory names and dangerous characters
        name = Path(filename).name
        cleaned = re.sub(r"[^\w\.\-]", "_", name)
        return cleaned or "unnamed_file"

    @classmethod
    async def save_and_process_upload(
        cls,
        upload_file: UploadFile,
        db: Session,
    ) -> FileUploadResponse:
        start_time = time.perf_counter()

        original_filename = upload_file.filename or "uploaded_file"
        clean_name = cls.sanitize_filename(original_filename)
        suffix = Path(clean_name).suffix.lower()

        if suffix not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"File '{clean_name}' has an unsupported extension. Only {', '.join(settings.ALLOWED_EXTENSIONS)} are allowed.",
                details={"allowed_extensions": settings.ALLOWED_EXTENSIONS},
            )

        detected_type = FileType.KML if suffix == ".kml" else FileType.SHAPEFILE
        file_id = str(uuid.uuid4())
        saved_filename = f"{file_id}_{clean_name}"
        storage_path = settings.UPLOAD_DIR / saved_filename

        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Read content while tracking size
        file_size = 0
        with open(storage_path, "wb") as f_out:
            while chunk := await upload_file.read(1024 * 64):  # 64KB chunks
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE_BYTES:
                    f_out.close()
                    storage_path.unlink(missing_ok=True)
                    raise FileSizeExceededError(
                        max_size_bytes=settings.MAX_FILE_SIZE_BYTES,
                        actual_size_bytes=file_size,
                    )
                f_out.write(chunk)

        if file_size == 0:
            storage_path.unlink(missing_ok=True)
            raise EmptyFileError()

        # Create database record in PENDING state
        file_record = UploadedFileModel(
            id=file_id,
            filename=clean_name,
            file_type=detected_type,
            file_size_bytes=file_size,
            storage_path=str(storage_path),
            status=FileProcessingStatus.PROCESSING,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        temp_dir: Optional[Path] = None
        try:
            # Parse geospatial features
            gdf, temp_dir = GeospatialProcessor.load_geodataframe(
                storage_path,
                "kml" if detected_type == FileType.KML else "shapefile",
            )

            source_crs, projected_crs, measurement_items, summary = (
                GeospatialProcessor.process_measurements(gdf)
            )

            # Insert measurement rows
            for m in measurement_items:
                meas_model = FeatureMeasurementModel(
                    file_id=file_id,
                    feature_index=m["feature_index"],
                    geometry_type=m["geometry_type"],
                    measurement_type=m["measurement_type"],
                    measurement_value=m["measurement_value"],
                    unit=m["unit"],
                    status=m["status"],
                    properties=m["properties"],
                    geometry_geojson=m["geometry_geojson"],
                )
                db.add(meas_model)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            file_record.source_crs = source_crs
            file_record.projected_crs = projected_crs
            file_record.feature_count = len(gdf)
            file_record.status = FileProcessingStatus.COMPLETED
            file_record.processing_time_ms = round(elapsed_ms, 2)
            db.commit()
            db.refresh(file_record)

            return FileUploadResponse(
                id=file_record.id,
                filename=file_record.filename,
                file_type=file_record.file_type.value,
                file_size_bytes=file_record.file_size_bytes,
                feature_count=file_record.feature_count,
                source_crs=file_record.source_crs,
                projected_crs=file_record.projected_crs,
                status=file_record.status.value,
                processing_time_ms=file_record.processing_time_ms,
                created_at=file_record.created_at,
            )

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            file_record.status = FileProcessingStatus.FAILED
            file_record.error_message = str(ex)
            file_record.processing_time_ms = round(elapsed_ms, 2)
            db.commit()
            logger.error(f"Failed processing file {file_id}: {ex}", exc_info=True)
            raise
        finally:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def get_file_by_id(file_id: str, db: Session) -> FileDetailResponse:
        file_record = db.query(UploadedFileModel).filter(UploadedFileModel.id == file_id).first()
        if not file_record:
            raise EntityNotFoundError("File", file_id)

        return FileDetailResponse(
            id=file_record.id,
            filename=file_record.filename,
            file_type=file_record.file_type.value,
            file_size_bytes=file_record.file_size_bytes,
            feature_count=file_record.feature_count,
            source_crs=file_record.source_crs,
            projected_crs=file_record.projected_crs,
            status=file_record.status.value,
            error_message=file_record.error_message,
            processing_time_ms=file_record.processing_time_ms,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )

    @staticmethod
    def list_files(
        db: Session,
        limit: int = 20,
        offset: int = 0,
    ) -> FileListResponse:
        total = db.query(func.count(UploadedFileModel.id)).scalar() or 0
        records = (
            db.query(UploadedFileModel)
            .order_by(UploadedFileModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [
            FileListItem(
                id=r.id,
                filename=r.filename,
                file_type=r.file_type.value,
                file_size_bytes=r.file_size_bytes,
                feature_count=r.feature_count,
                source_crs=r.source_crs,
                projected_crs=r.projected_crs,
                status=r.status.value,
                processing_time_ms=r.processing_time_ms,
                created_at=r.created_at,
            )
            for r in records
        ]

        return FileListResponse(
            items=items,
            pagination={"total": total, "limit": limit, "offset": offset},
        )

    @staticmethod
    def get_measurements_by_file_id(file_id: str, db: Session) -> FileMeasurementsResponse:
        file_record = db.query(UploadedFileModel).filter(UploadedFileModel.id == file_id).first()
        if not file_record:
            raise EntityNotFoundError("File", file_id)

        measurements = (
            db.query(FeatureMeasurementModel)
            .filter(FeatureMeasurementModel.file_id == file_id)
            .order_by(FeatureMeasurementModel.feature_index.asc())
            .all()
        )

        polygon_count = 0
        total_area_sq_m = 0.0
        line_count = 0
        total_length_m = 0.0
        point_count = 0
        unsupported_count = 0

        measurement_items = []
        for m in measurements:
            if m.geometry_type in ("Polygon", "MultiPolygon") and m.status == "COMPLETED":
                polygon_count += 1
                total_area_sq_m += m.measurement_value or 0.0
            elif m.geometry_type in ("LineString", "MultiLineString") and m.status == "COMPLETED":
                line_count += 1
                total_length_m += m.measurement_value or 0.0
            elif m.geometry_type in ("Point", "MultiPoint"):
                point_count += 1
            else:
                unsupported_count += 1

            measurement_items.append(
                FeatureMeasurementItem(
                    feature_id=m.feature_index,
                    geometry_type=m.geometry_type,
                    measurement_type=m.measurement_type,
                    value=m.measurement_value,
                    unit=m.unit,
                    status=m.status,
                    properties=m.properties or {},
                    geometry_geojson=m.geometry_geojson,
                )
            )

        summary = MeasurementSummary(
            total_features=len(measurements),
            polygon_count=polygon_count,
            total_area_sq_m=round(total_area_sq_m, 4),
            total_area_hectares=round(total_area_sq_m / 10000.0, 4),
            line_count=line_count,
            total_length_m=round(total_length_m, 4),
            point_count=point_count,
            unsupported_count=unsupported_count,
        )

        return FileMeasurementsResponse(
            file_id=file_id,
            source_crs=file_record.source_crs,
            projected_crs=file_record.projected_crs,
            summary=summary,
            measurements=measurement_items,
        )

    @staticmethod
    def delete_file(file_id: str, db: Session) -> None:
        file_record = db.query(UploadedFileModel).filter(UploadedFileModel.id == file_id).first()
        if not file_record:
            raise EntityNotFoundError("File", file_id)

        # Remove from disk
        try:
            path = Path(file_record.storage_path)
            if path.exists():
                path.unlink()
        except Exception as ex:
            logger.warning(f"Failed deleting file on disk {file_record.storage_path}: {ex}")

        # Cascade deletes measurements in DB
        db.delete(file_record)
        db.commit()
