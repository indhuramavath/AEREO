from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class FeatureMeasurementModel(Base):
    __tablename__ = "feature_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    geometry_type = Column(String(64), nullable=False)

    measurement_type = Column(String(32), nullable=True)  # "area", "length", or null
    measurement_value = Column(Float, nullable=True)
    unit = Column(String(16), nullable=True)  # "m²", "m", or null
    status = Column(String(32), nullable=False)  # "COMPLETED", "NOT_SUPPORTED", "EMPTY_GEOMETRY", etc.

    properties = Column(JSON, nullable=True)
    geometry_geojson = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    file = relationship("UploadedFileModel", back_populates="measurements")
