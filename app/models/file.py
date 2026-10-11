import enum
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class FileProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileType(str, enum.Enum):
    KML = "kml"
    SHAPEFILE = "shapefile"


class UploadedFileModel(Base):
    __tablename__ = "uploaded_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)

    source_crs = Column(String(64), nullable=True)
    projected_crs = Column(String(64), nullable=True)
    feature_count = Column(Integer, default=0, nullable=False)

    status = Column(Enum(FileProcessingStatus), default=FileProcessingStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    measurements = relationship(
        "FeatureMeasurementModel",
        back_populates="file",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
